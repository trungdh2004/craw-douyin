# 04: Công cụ Crawl theo ID / Link Chia Sẻ (Chạy ngay & Hẹn giờ 1 lần)

**What to build:** Người vận hành có thể nhập một hoặc nhiều dòng chứa `aweme_id`, URL đầy đủ (`douyin.com/video/...`, `/note/...`) hoặc văn bản chia sẻ chứa link rút gọn (`v.douyin.com/...`) trên trang Crawl theo ID / Link, chọn chạy ngay hoặc hẹn giờ chạy 1 lần (`run_at`), kèm tuỳ chọn tự động tải luôn file media không logo và tự động gắn Bookmark.

**Blocked by:** 02: Thư viện Bài đăng Giàu Metadata, Thời lượng Video (`MM:SS`) & Modal Xem Trước Media.

**Status:** ready-for-agent

- [x] Bộ phân giải định danh bóc tách chính xác `aweme_id` từ chuỗi số thuần, URL đầy đủ hoặc đoạn văn bản chia sẻ có chứa link rút gọn `v.douyin.com`.
- [x] Endpoint `POST /api/crawl/items` nhận danh sách đầu vào cùng các tuỳ chọn `auto_download`, `is_bookmarked`, `bookmark_collection`, và `run_at`.
- [x] Khi chạy ngay, hệ thống trích xuất chi tiết bài đăng, tải ảnh bìa, lưu vào cơ sở dữ liệu (kèm Bookmark nếu chọn) và kích hoạt tải media không logo nếu `auto_download = True`.
- [x] Khi có `run_at` trong tương lai, hệ thống đăng ký lịch chạy 1 lần (`DateTrigger`) vào bộ lập lịch và tự động thực thi khi đến giờ.
- [x] Giao diện trang Crawl theo ID / Link cho phép nhập nhiều dòng, cấu hình tuỳ chọn chạy ngay / hẹn giờ, tự động tải / bookmark và theo dõi kết quả.
- [x] Kiểm thử tích hợp xác nhận việc phân giải `aweme_id` từ nhiều định dạng đầu vào, chạy ngay kèm tải media tự động, và đặt lịch chạy 1 lần.
