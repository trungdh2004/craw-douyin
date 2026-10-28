# Admin Authentication & Session Protection

Status: resolved

## Problem Statement

Hiện tại toàn bộ bảng điều khiển Douyin Crawler và các điểm cuối API quản trị đều mở hoàn toàn mà không có lớp xác thực người dùng. Khi ứng dụng được chạy trên máy chủ hoặc mở cổng trong mạng nội bộ/Internet, bất kỳ ai biết địa chỉ IP và cổng đều có thể truy cập kho video, thay đổi cấu hình chống bot, chỉnh sửa lịch quét, xem nhật ký hệ thống, mở trình duyệt phiên Douyin hoặc đẩy video sang Server Phân tích trái phép.

## Solution

Bổ sung cơ chế xác thực một tài khoản Quản trị viên duy nhất (Single Admin Authentication) bảo vệ toàn bộ giao diện bảng điều khiển và các API của hệ thống:

- Khởi tạo tài khoản Admin mặc định từ cấu hình môi trường (hoặc thông tin mặc định ban đầu `admin` / `admin123` nếu chưa cấu hình), lưu trữ mật khẩu dưới dạng băm an toàn trong cơ sở dữ liệu.
- Hiển thị màn hình Đăng nhập tối giản, đồng bộ với phong cách giao diện tối (Quiet Dark) khi người vận hành chưa đăng nhập.
- Sử dụng phiên đăng nhập tạm thời theo phiên trình duyệt (Session-only: kết hợp Session Cookie không lưu `Max-Age` và cờ phiên trong `sessionStorage` của trình duyệt) để đảm bảo mỗi khi người vận hành đóng trình duyệt/tab hoặc nhấn Đăng xuất, phiên làm việc sẽ tự động kết thúc ngay lập tức.
- Cho phép Quản trị viên đổi tên đăng nhập (Username) và mật khẩu (Password) trực tiếp ngay trên giao diện Cài đặt.
- Bảo vệ toàn bộ các API quản trị, đồng thời vẫn cho phép các điểm cuối kiểm tra sức khỏe hệ thống và điểm cuối tích hợp nội bộ phục vụ Server Phân tích hoạt động bình thường.

## User Stories

1. As an operator, I want to see a login screen when I open the Douyin Crawler dashboard in a new browser session, so that unauthorized users cannot view or control my crawler data.
2. As an operator, I want to sign in with my Admin username and password, so that I can unlock full access to the dashboard.
3. As an operator, I want to see a clear Vietnamese error message when I enter an incorrect username or password, so that I know why sign-in failed and can retry.
4. As an operator, I want the initial Admin credentials to be automatically seeded from environment configuration (defaulting to `admin` / `admin123` if not set), so that I can log in immediately on first deployment without manual database setup.
5. As an operator, I want my login session to automatically terminate as soon as I close my browser or tab, so that nobody using the machine afterward can access my session without logging in again.
6. As an operator, I want a Logout button in the sidebar footer, so that I can explicitly end my active session at any time.
7. As an operator, I want my active session to seamlessly authenticate media requests such as video cover thumbnails, album images, and MP4 video streams, so that media previews in the library and preview dialog work without broken images or extra prompts.
8. As an operator, I want unauthenticated API calls to management endpoints to be rejected with an HTTP 401 status, so that external scripts or unauthorized users cannot bypass the UI to query or mutate crawler data.
9. As an operator, I want the dashboard to automatically return to the login screen if the backend rejects a request with HTTP 401 (e.g., after server restart or session invalidation), so that I am never stuck on a broken dashboard state.
10. As an operator, I want to view my current Admin username in the settings view, so that I know which account is currently active.
11. As an operator, I want to change my Admin username and password from within the dashboard by verifying my current password, so that I can rotate my credentials without editing server files or database rows manually.
12. As an operator, I want password updates to reject a wrong current password or a mismatched confirmation password with a clear error message, so that I do not accidentally lock myself out due to a typo.
13. As an operator, I want my Admin password to be stored as a salted cryptographic hash in the database rather than plaintext, so that credentials remain safe if the database is inspected.
14. As a system health monitor, I want the healthcheck endpoint to remain accessible without authentication, so that startup scripts and container health probes can verify the service is up.
15. As the external Edit Studio service, I want the MP4 resolution bridge endpoint to remain accessible for integration requests, so that video analysis workflows are not blocked by browser session cookies.

## Implementation Decisions

- **Single-Admin Credential Storage**:
  - Lưu trữ thông tin tài khoản Admin duy nhất trong cơ sở dữ liệu (mở rộng bảng cấu hình đơn bản hiện có hoặc bảng cấu hình xác thực đơn bản với `admin_username`, `admin_password_hash`, `admin_session_secret`).
  - Khi hệ thống khởi tạo lần đầu và chưa có mật khẩu băm trong cơ sở dữ liệu, tự động lấy giá trị khởi tạo từ cấu hình môi trường (`ADMIN_USERNAME`, mặc định `admin`; `ADMIN_PASSWORD`, mặc định `admin123`), băm bằng thuật toán `PBKDF2-HMAC-SHA256` kèm salt ngẫu nhiên và lưu vào cơ sở dữ liệu.
- **Session-Only Token & Dual-Guard Expiration**:
  - Khi đăng nhập thành công, máy chủ phát hành một mã phiên có chữ ký HMAC (`session_token`) và gắn vào **Session Cookie** (`HttpOnly`, `SameSite=Lax`, không đặt `Max-Age` hay `Expires`) đồng thời trả mã phiên về trong phản hồi JSON.
  - Phía giao diện lưu trạng thái phiên vào `window.sessionStorage` (bộ nhớ tự xóa sạch ngay khi đóng tab/trình duyệt). Khi ứng dụng tải lên, nếu `window.sessionStorage` không có cờ phiên hợp lệ, giao diện sẽ chủ động gọi điểm cuối đăng xuất để xóa mọi Session Cookie còn sót lại (trong trường hợp trình duyệt bật chế độ khôi phục tab cũ) và hiển thị màn hình Đăng nhập.
- **Authentication API Contracts**:
  - `GET /api/auth/status`: Kiểm tra trạng thái xác thực hiện tại, trả về `{ authenticated: bool, username: str | null }`.
  - `POST /api/auth/login`: Nhận `{ username: str, password: str }`. Nếu hợp lệ, thiết lập Session Cookie và trả về `{ authenticated: true, username: str, token: str }`; nếu sai thông tin, trả về HTTP `401` kèm thông báo lỗi tiếng Việt.
  - `POST /api/auth/logout`: Xóa Session Cookie hiện tại và trả về `{ authenticated: false }`.
  - `PUT /api/auth/password`: Yêu cầu đã xác thực; nhận `{ current_password: str, new_username: str | None, new_password: str }`. Kiểm tra `current_password` khớp với bản băm hiện tại, cập nhật `admin_username` (nếu có) và `admin_password_hash` mới, đồng thời xoay vòng `admin_session_secret` và cấp lại Session Cookie mới cho phiên hiện tại.
- **API Protection Middleware**:
  - Áp dụng lớp kiểm tra xác thực cho các đường dẫn bắt đầu bằng `/api/`.
  - Các đường dẫn được miễn kiểm tra phiên đăng nhập trình duyệt: `/api/auth/status`, `/api/auth/login`, `/api/auth/logout`, `/api/health`, và `/api/videos/resolve-mp4`.
  - Chấp nhận xác thực qua Session Cookie hoặc header `Authorization: Bearer <token>`.
  - Cho phép cấu hình bật/tắt bắt buộc xác thực trong môi trường kiểm thử tự động thông qua tham số khởi tạo ứng dụng (`require_auth: bool = False` mặc định trong hàm tạo ứng dụng kiểm thử hoặc bật mặc định khi chạy sản phẩm, hoặc tự động xác thực cho các bài kiểm thử hiện có để không phá vỡ bộ kiểm thử hồi quy).
- **Dashboard Login & Account Settings UI**:
  - Khi chưa xác thực (`authenticated === false`), chỉ hiển thị màn hình Đăng nhập toàn trang theo tông màu tối đơn sắc (Quiet Dark) với ô nhập Tên đăng nhập, Mật khẩu và nút Đăng nhập.
  - Khi đã xác thực, hiển thị bảng điều khiển đầy đủ, bổ sung nút **Đăng xuất** ở khung trạng thái góc dưới thanh điều hướng bên trái, và bổ sung thẻ **Tài khoản Admin (Đổi mật khẩu)** trong khu vực cài đặt.

## Testing Decisions

- **Thế nào là một bài kiểm thử tốt**: Chỉ kiểm thử hành vi quan sát được từ bên ngoài (mã trạng thái HTTP, dữ liệu JSON trả về, cookie phiên, và giao diện hiển thị cho người dùng), không kiểm thử chi tiết cài đặt nội bộ như hàm băm hay cấu trúc cột cơ sở dữ liệu.
- **Các điểm neo kiểm thử (Seams)**:
  1. **Backend HTTP API Seam**: Kiểm thử thông qua ứng dụng FastAPI khởi tạo với cơ sở dữ liệu PostgreSQL thực tế và trình khách HTTP bất đồng bộ:
     - Truy cập `/api/stats` hoặc `/api/videos` khi chưa đăng nhập trả về HTTP `401`.
     - Truy cập `/api/health` và `/api/videos/resolve-mp4` khi chưa đăng nhập vẫn hoạt động bình thường.
     - Đăng nhập sai mật khẩu tại `POST /api/auth/login` trả về HTTP `401`; đăng nhập đúng trả về HTTP `200`, thiết lập cookie phiên và mở khóa các lệnh gọi `/api/*`.
     - Đổi mật khẩu tại `PUT /api/auth/password` với mật khẩu cũ đúng sẽ cập nhật thành công; mật khẩu cũ không còn dùng để đăng nhập được nữa và mật khẩu mới đăng nhập thành công.
     - Gọi `POST /api/auth/logout` xóa phiên và khiến các lệnh gọi `/api/*` tiếp theo trả về HTTP `401`.
  2. **Frontend UI Seam**: Kiểm thử thông qua việc render thành phần ứng dụng gốc với Testing Library:
     - Hiển thị màn hình đăng nhập khi chưa có phiên trong `sessionStorage` hoặc `/api/auth/status` trả về `authenticated: false`.
     - Cho phép nhập Username & Password, gửi biểu mẫu đăng nhập và chuyển vào màn hình Tổng quan sau khi thành công.
     - Cho phép bấm nút Đăng xuất để quay về màn hình đăng nhập và xóa phiên trong `sessionStorage`.
- **Tiền lệ kiểm thử trong dự án**: Tuân theo mẫu kiểm thử tích hợp FastAPI + PostgreSQL hiện có và mẫu kiểm thử giao diện với Vitest + Testing Library.

## Out of Scope

- Quản lý nhiều người dùng (Multi-user) hoặc phân quyền theo vai trò (RBAC).
- Đăng nhập qua bên thứ ba (OAuth2, Google, SSO) hoặc xác thực hai yếu tố (2FA/TOTP).
- Khôi phục mật khẩu qua email (do ứng dụng chạy độc lập nội bộ).

## Further Notes

- Để tránh làm hỏng các bài kiểm thử tích hợp hiện có vốn giả định gọi thẳng `/api/*`, hàm khởi tạo ứng dụng có thể hỗ trợ cờ cấu hình hoặc cho phép bật chế độ xác thực thông qua cấu hình ứng dụng, đồng thời có bộ kiểm thử riêng kiểm tra đầy đủ luồng chặn `401`, đăng nhập, đổi mật khẩu và đăng xuất.
