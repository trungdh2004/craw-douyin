# 04: Quản lý mục tiêu và thu thập kết quả theo từ khóa

**What to build:** Người vận hành có thể quản lý mục tiêu tìm kiếm, lên lịch hoặc chạy ngay để thu thập một lượng giới hạn bài theo từ khóa, lưu metadata và cover mà không tự tải media nặng.

**Blocked by:** 01: Khởi tạo ứng dụng và lưu trữ Douyin; 02: Đăng nhập Douyin bằng phiên trình duyệt lưu bền vững.

**Status:** ready-for-agent

- [ ] Người vận hành tạo, sửa, bật/tắt và xóa mục tiêu từ khóa kèm lịch Cron và giới hạn số bài mỗi lần chạy.
- [ ] Mọi thay đổi mục tiêu được đồng bộ với bộ lập lịch; thao tác Run Now khởi chạy tác vụ nền.
- [ ] Kết quả tìm kiếm được chuẩn hóa và lưu đầy đủ metadata, nguồn mục tiêu và cover local.
- [ ] Một phiên không thu thập quá giới hạn cấu hình, không quét chi tiết bình luận và không tự tải video hoặc album ảnh gốc.
- [ ] Lịch sử chạy phản ánh đúng kết quả thành công hoặc lỗi cùng số bài mới và cập nhật.
- [ ] Kiểm thử tích hợp xác nhận giới hạn số bài, chống trùng lặp, cover local và trạng thái media `NONE`.
