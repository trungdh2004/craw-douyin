# 06: Tải một bài theo yêu cầu và tự làm mới link hết hạn

**What to build:** Người vận hành có thể bấm lưu một bài từ thư viện; hệ thống tải ngầm video không logo hoặc toàn bộ ảnh gốc vào thư mục có tổ chức, đồng thời tự làm mới URL Douyin đã hết hạn.

**Blocked by:** 03: Quản lý mục tiêu và tự động thu thập bài mới theo kênh; 05: Thư viện bài đăng có lọc, sắp xếp và xem trước.

**Status:** ready-for-agent

- [ ] Thao tác Lưu Video chuyển trạng thái quan sát được từ `NONE` sang `DOWNLOADING`, rồi `COMPLETED` hoặc `FAILED`.
- [ ] Video không logo được lưu theo kênh, ngày đăng và `aweme_id`; bài album lưu đầy đủ danh sách ảnh gốc trong cùng cấu trúc tương ứng.
- [ ] Khi URL đã quá `x-expires` hoặc trả về HTTP 403, hệ thống lấy chi tiết mới theo `aweme_id`, cập nhật URL và thử tải lại.
- [ ] Khi hoàn tất, thư viện hiển thị trạng thái, thời điểm tải và đường dẫn local; khi thất bại, lỗi được lưu để người vận hành nhận biết.
- [ ] Kiểm thử tích hợp xác nhận cả trường hợp URL còn hạn, URL hết hạn được làm mới và lỗi không thể phục hồi.
