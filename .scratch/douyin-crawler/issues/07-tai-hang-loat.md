# 07: Tải hàng loạt các bài đã chọn

**What to build:** Người vận hành có thể chọn nhiều bài trong thư viện và khởi chạy tải hàng loạt, sau đó theo dõi kết quả độc lập của từng video hoặc album.

**Blocked by:** 06: Tải một bài theo yêu cầu và tự làm mới link hết hạn.

**Status:** ready-for-agent

- [ ] Dashboard cho phép chọn nhiều bài và gửi một yêu cầu tải hàng loạt.
- [ ] Yêu cầu hợp lệ được tiếp nhận để xử lý nền mà không chờ toàn bộ tệp tải xong.
- [ ] Mỗi bài sử dụng cùng hành vi tải, cấu trúc lưu và làm mới URL như thao tác tải đơn.
- [ ] Thành công hoặc thất bại của một bài không làm mất kết quả của các bài còn lại, và trạng thái từng bài được hiển thị riêng.
- [ ] Kiểm thử tích hợp xác nhận lô gồm video, album, URL hết hạn và một mục tải thất bại.
