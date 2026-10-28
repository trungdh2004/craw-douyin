# 02 - Frontend Login Screen, Session-Only Guard & Admin Account Settings

Status: resolved
Blocked by: 01

## Summary

Implement the Quiet Dark login screen, `sessionStorage` + session-cookie dual guard (auto-logout on browser close), Sidebar Logout button, automatic `401` redirect to login, and the Admin Password/Username update card in Settings as specified in `.scratch/admin-authentication/spec.md`.

## Acceptance Criteria

1. On startup, check `sessionStorage.getItem('douyin_auth_active')` and `GET /api/auth/status`:
   - If `sessionStorage` does not have an active session marker in real browser mode, call `POST /api/auth/logout` and present the Login screen.
   - Attach `Authorization: Bearer <token>` (if stored in `sessionStorage`) and `credentials: 'same-origin'` on `apiFetch`, and automatically transition to the Login screen if any `/api/*` call returns HTTP `401`.
2. Render a clean, Quiet Dark login screen when unauthenticated with Username & Password inputs, error feedback, and submit button.
3. Add a **Đăng xuất** button in the Sidebar footer (with confirmation or immediate session clear) that calls `POST /api/auth/logout`, clears `sessionStorage`, and returns to the Login screen.
4. Add a **Tài khoản Admin (Đổi mật khẩu)** card in Settings allowing the operator to change `Username` and `Mật khẩu mới` by entering `Mật khẩu hiện tại`.
5. Verify via Vitest + Testing Library tests in `frontend/src/App.test.tsx` and ensure `bun run build` succeeds.
