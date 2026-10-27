# 01: Khung ứng dụng Vite + shadcn/ui Left Sidebar & Trang Tổng Quan Hệ Thống

**What to build:** Người vận hành có thể truy cập ứng dụng Frontend SPA được xây dựng bằng Vite, React, TypeScript, TailwindCSS và `shadcn/ui` với bố cục Left Sidebar cố định bên trái (7 mục điều hướng), thanh trạng thái toàn cục (hiển thị phiên đăng nhập Douyin, nút mở trình duyệt QR, trạng thái Scheduler) và trang Tổng quan hiển thị các chỉ số thống kê toàn hệ thống từ API `/api/stats`.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] Khởi tạo ứng dụng Frontend trong thư mục `frontend/` với Vite, React, TypeScript, TailwindCSS, `lucide-react` và các component chuẩn `shadcn/ui`, cấu hình proxy `/api` trong dev và phục vụ bản build tĩnh từ FastAPI.
- [x] Left Sidebar cố định bên trái điều hướng mượt mà giữa 7 phân khu: Tổng quan, Thư viện Video, Đã Bookmark, Crawl theo ID / Link, Mục tiêu & Hẹn giờ, Lịch sử chạy, và Cấu hình Chống Bot.
- [x] Thanh trạng thái toàn cục hiển thị trạng thái phiên đăng nhập Douyin, nút mở Chromium để quét QR / giải Captcha, số tác vụ đang chạy và trạng thái của bộ lập lịch.
- [x] Endpoint `GET /api/stats` trả về số liệu tổng hợp (tổng số bài đăng, số bài đã tải xong, số bài đã Bookmark, số mục tiêu đang bật, số tác vụ đang chạy và thống kê trạng thái lịch sử) để hiển thị trên trang Tổng quan.
- [x] Kiểm thử tích hợp xác nhận `GET /api/stats` trả về đúng số liệu thống kê thực tế và ứng dụng phục vụ giao diện Dashboard thành công.
