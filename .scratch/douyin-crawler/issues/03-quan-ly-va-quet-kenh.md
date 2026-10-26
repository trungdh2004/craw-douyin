# 03: Quản lý mục tiêu và tự động thu thập bài mới theo kênh

**What to build:** Người vận hành có thể quản lý mục tiêu kênh, lên lịch hoặc chạy quét ngay; hệ thống lưu metadata và cover của bài mới, cập nhật bài cũ, dừng quét tăng dần đúng lúc và ghi lại kết quả phiên chạy mà không tự tải video.

**Blocked by:** 01: Khởi tạo ứng dụng và lưu trữ Douyin; 02: Đăng nhập Douyin bằng phiên trình duyệt lưu bền vững.

**Status:** ready-for-agent

- [ ] Người vận hành tạo, sửa, bật/tắt và xóa mục tiêu kênh bằng URL hoặc `sec_uid`, kèm lịch Cron và giới hạn mỗi lần chạy.
- [ ] Mọi thay đổi mục tiêu được đồng bộ với bộ lập lịch; thao tác Run Now khởi chạy tác vụ nền mà không chờ lịch.
- [ ] Phiên quét lưu hoặc cập nhật đầy đủ metadata đã nêu trong đặc tả và tải cover về ổ cứng, nhưng giữ trạng thái tải media là `NONE`.
- [ ] Tối đa ba bài ghim cũ đầu kênh được bỏ qua khỏi bộ đếm dừng nhưng vẫn được cập nhật chỉ số tương tác.
- [ ] Phiên quét dừng khi gặp liên tiếp ba bài thường đã tồn tại hoặc đạt giới hạn của mục tiêu.
- [ ] Lịch sử chạy ghi nhận thời gian, trạng thái, số bài mới, số bài cập nhật và lỗi nếu có.
- [ ] Kiểm thử tích hợp xác nhận luồng bài ghim, bài mới, ba bài thường cũ, cover local và việc không tải video.
