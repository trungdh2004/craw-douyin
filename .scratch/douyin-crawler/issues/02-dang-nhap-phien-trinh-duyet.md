# 02: Đăng nhập Douyin bằng phiên trình duyệt lưu bền vững

**What to build:** Người vận hành có thể mở Chromium từ Dashboard để quét QR, xem trạng thái đăng nhập và tái sử dụng phiên Douyin trong những lần chạy sau mà không phải nhập lại Cookie thủ công.

**Blocked by:** 01: Khởi tạo ứng dụng và lưu trữ Douyin.

**Status:** ready-for-agent

- [ ] Dashboard và REST API hiển thị được trạng thái phiên đăng nhập hiện tại.
- [ ] Thao tác đăng nhập mở Chromium có giao diện để người vận hành quét QR hoặc xử lý Captcha.
- [ ] Trạng thái phiên được lưu trong persistent profile và vẫn dùng được sau khi khởi động lại ứng dụng.
- [ ] Các yêu cầu dùng chung profile được tuần tự hóa để không có hai phiên Chromium xung đột.
- [ ] Kiểm thử tích hợp sử dụng adapter Douyin giả lập để xác nhận giao kèo trạng thái và đăng nhập.
