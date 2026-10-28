from datetime import UTC, datetime
import hashlib
import hmac
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from douyin_crawler.anti_bot import get_or_create_anti_bot_settings
from douyin_crawler.models import AntiBotSettings
from douyin_crawler.settings import get_settings

SESSION_COOKIE_NAME = "douyin_session"
PBKDF2_ITERATIONS = 150_000

PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/status",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/videos/resolve-mp4",
}


def is_public_api_path(path: str) -> bool:
    if path in PUBLIC_API_PATHS:
        return True
    if path.startswith("/api/videos/"):
        if (
            path.endswith("/cover")
            or path.endswith("/stream")
            or "/images/" in path
        ):
            return True
    return False


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    authenticated: bool
    username: str
    token: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_username: str | None = Field(default=None, max_length=128)
    new_password: str = Field(min_length=4, max_length=256)


def hash_password(password: str, salt: str | None = None) -> str:
    chosen_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        chosen_salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${chosen_salt}${derived}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
    except ValueError:
        return False
    salt = parts[2]
    expected_hex = parts[3]
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return hmac.compare_digest(derived, expected_hex)


def create_session_token(username: str, secret: str) -> str:
    issued_at = str(int(time.time()))
    payload = f"{username}:{issued_at}"
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def verify_session_token(
    token: str | None,
    expected_username: str | None,
    secret: str | None,
) -> bool:
    if not token or not expected_username or not secret:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    username, issued_at, signature = parts
    if not hmac.compare_digest(username, expected_username):
        return False
    payload = f"{username}:{issued_at}"
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_sig)


async def ensure_admin_credentials(session: AsyncSession) -> AntiBotSettings:
    settings = await get_or_create_anti_bot_settings(session)
    env_settings = get_settings()
    changed = False
    if not settings.admin_username:
        settings.admin_username = env_settings.admin_username or "admin"
        changed = True
    if not settings.admin_password_hash:
        settings.admin_password_hash = hash_password(env_settings.admin_password or "admin123")
        changed = True
    if not settings.admin_session_secret:
        settings.admin_session_secret = secrets.token_hex(32)
        changed = True
    if changed:
        settings.updated_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(settings)
    return settings


def extract_token_from_request(request: Request) -> str | None:
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()
        if bearer_token:
            return bearer_token
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip()
    query_token = request.query_params.get("token")
    if query_token:
        return query_token.strip()
    return None


async def get_authenticated_username(
    request: Request,
    sessions: async_sessionmaker[AsyncSession],
) -> str | None:
    token = extract_token_from_request(request)
    if not token:
        return None
    async with sessions() as session:
        settings = await ensure_admin_credentials(session)
        if verify_session_token(
            token,
            settings.admin_username,
            settings.admin_session_secret,
        ):
            return settings.admin_username
    return None


def set_session_cookie(response: Response, token: str) -> None:
    # Browser session-only cookie: omit max_age and expires so closing browser clears it
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )


def create_auth_router(
    sessions: async_sessionmaker[AsyncSession],
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.get("/status")
    async def auth_status(request: Request, response: Response) -> AuthStatusResponse:
        username = await get_authenticated_username(request, sessions)
        if username:
            token = extract_token_from_request(request)
            if token and request.cookies.get(SESSION_COOKIE_NAME) != token:
                set_session_cookie(response, token)
            return AuthStatusResponse(authenticated=True, username=username)
        return AuthStatusResponse(authenticated=False, username=None)

    @router.post("/login")
    async def login(payload: LoginRequest, response: Response) -> LoginResponse:
        async with sessions() as session:
            settings = await ensure_admin_credentials(session)
            clean_user = payload.username.strip()
            user_ok = hmac.compare_digest(clean_user, settings.admin_username or "admin")
            pw_ok = verify_password(payload.password, settings.admin_password_hash)
            if not (user_ok and pw_ok):
                raise HTTPException(
                    status_code=401,
                    detail="Sai tên đăng nhập hoặc mật khẩu",
                )
            token = create_session_token(
                settings.admin_username,
                settings.admin_session_secret or secrets.token_hex(32),
            )
            set_session_cookie(response, token)
            return LoginResponse(
                authenticated=True,
                username=settings.admin_username,
                token=token,
            )

    @router.post("/logout")
    async def logout(response: Response) -> AuthStatusResponse:
        response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
        return AuthStatusResponse(authenticated=False, username=None)

    @router.put("/password")
    async def change_password(
        payload: PasswordChangeRequest,
        request: Request,
        response: Response,
    ) -> LoginResponse:
        username = await get_authenticated_username(request, sessions)
        if not username:
            raise HTTPException(status_code=401, detail="Vui lòng đăng nhập lại")
        async with sessions() as session:
            settings = await ensure_admin_credentials(session)
            if not verify_password(payload.current_password, settings.admin_password_hash):
                raise HTTPException(
                    status_code=400,
                    detail="Mật khẩu hiện tại không chính xác",
                )
            next_username = (payload.new_username or "").strip() or settings.admin_username
            settings.admin_username = next_username
            settings.admin_password_hash = hash_password(payload.new_password)
            settings.admin_session_secret = secrets.token_hex(32)
            settings.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(settings)
            token = create_session_token(
                settings.admin_username,
                settings.admin_session_secret,
            )
            set_session_cookie(response, token)
            return LoginResponse(
                authenticated=True,
                username=settings.admin_username,
                token=token,
            )

    return router
