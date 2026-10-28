# 01 - Backend Admin Authentication API & Protection Middleware

Status: resolved
Blocked by: none

## Summary

Implement single-admin authentication storage, password hashing (`PBKDF2-HMAC-SHA256`), session-only signed cookies/tokens, `/api/auth/*` endpoints, and `/api/*` protection middleware as specified in `.scratch/admin-authentication/spec.md`.

## Acceptance Criteria

1. Seed initial Admin credentials from `ADMIN_USERNAME` (default `admin`) and `ADMIN_PASSWORD` (default `admin123`) into the singleton settings row with a salted `PBKDF2-HMAC-SHA256` hash (`admin_username`, `admin_password_hash`, `admin_session_secret`).
2. Expose:
   - `GET /api/auth/status` -> `{ "authenticated": bool, "username": str | null }`
   - `POST /api/auth/login` -> validates `username` & `password`, sets HttpOnly session cookie (`douyin_session`, no `Max-Age`/`Expires`), returns `{ "authenticated": true, "username": str, "token": str }` or HTTP `401`.
   - `POST /api/auth/logout` -> clears `douyin_session` cookie and returns `{ "authenticated": false }`.
   - `PUT /api/auth/password` -> verifies `current_password`, updates `new_username` (optional) and `new_password`, rotates `admin_session_secret`, issues a fresh session cookie/token.
3. Protect `/api/*` routes when authentication is enabled (exempting `/api/auth/status`, `/api/auth/login`, `/api/auth/logout`, `/api/health`, and `/api/videos/resolve-mp4`). Accept either the `douyin_session` cookie or `Authorization: Bearer <token>`.
4. Verify via end-to-end HTTP tests in `tests/test_admin_auth.py` while keeping all existing tests passing.
