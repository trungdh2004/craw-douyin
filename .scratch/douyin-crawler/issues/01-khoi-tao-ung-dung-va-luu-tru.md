# 01: Khởi tạo ứng dụng và lưu trữ Douyin

**What to build:** Người vận hành có thể khởi chạy dịch vụ FastAPI hợp nhất cùng PostgreSQL và có nền tảng lưu trữ bền vững cho mục tiêu quét, bài đăng Douyin và lịch sử chạy.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] PostgreSQL có thể được khởi chạy bằng Docker Compose và ứng dụng kết nối được bằng cấu hình môi trường.
- [ ] Lược đồ dữ liệu lưu được mục tiêu quét, metadata bài đăng, trạng thái tải và lịch sử chạy theo đặc tả.
- [ ] Tiến trình FastAPI quản lý vòng đời của `AsyncIOScheduler` và phục vụ được REST API cùng Web Dashboard.
- [ ] Kiểm thử tích hợp xác nhận dữ liệu được ghi và đọc lại từ PostgreSQL dành cho test.
