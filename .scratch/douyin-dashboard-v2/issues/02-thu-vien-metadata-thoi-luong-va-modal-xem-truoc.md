# 02: Thư viện Bài đăng Giàu Metadata, Thời lượng Video (`MM:SS`) & Modal Xem Trước Media

**What to build:** Người vận hành duyệt danh sách bài đã crawl trên trang Thư viện Video (hỗ trợ cả `Grid View` và `Table View`) với đầy đủ metadata được hiển thị sẵn, bao gồm thời lượng phát của video (`MM:SS`), thời gian đăng bài, thời gian hệ thống thu thập, kích thước, nhạc nền, thông tin tác giả, 4 chỉ số tương tác, và có thể bấm vào bất kỳ bài nào để mở Modal Xem Trước phát trực tiếp video `.mp4` hoặc trình chiếu Album ảnh.

**Blocked by:** 01: Khung ứng dụng Vite + shadcn/ui Left Sidebar & Trang Tổng Quan Hệ Thống.

**Status:** ready-for-agent

- [x] Lược đồ dữ liệu và bộ thu thập trích xuất, lưu trữ thêm thời lượng video (`duration_ms`), chiều rộng (`width`), chiều cao (`height`), tên nhạc nền (`music_title`) và tác giả nhạc (`music_author`).
- [x] `GET /api/videos` trả về đầy đủ metadata mở rộng kèm `duration_ms`, `create_time`, `crawled_at`, hỗ trợ lọc theo khoảng thời lượng (`min_duration_ms`, `max_duration_ms`) và sắp xếp theo `duration_ms`.
- [x] Bổ sung endpoint phát media trực tiếp từ ổ cứng (`GET /api/videos/{aweme_id}/stream` cho video `.mp4` và `GET /api/videos/{aweme_id}/images/{index}` cho ảnh trong Album) phục vụ trình phát xem trước.
- [x] Giao diện Thư viện Video hiển thị sẵn badge thời lượng `MM:SS` (hoặc số ảnh Album) trên ảnh bìa, đầy đủ metadata và các mốc thời gian ở cả chế độ Lưới (`Grid View`) lẫn Bảng (`Table View`), kèm Modal Xem Trước (`shadcn Dialog`).
- [x] Kiểm thử tích hợp xác nhận việc lưu trữ, lọc/sắp xếp theo `duration_ms`, trả về đầy đủ metadata và phát luồng media local sau khi tải xong.
