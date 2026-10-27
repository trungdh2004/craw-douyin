# 07: Lịch sử Chạy Chi tiết (Execution History), Chạy lại (Retry) & Dọn dẹp Logs

**What to build:** Người vận hành theo dõi toàn bộ lịch sử thực thi của mọi loại tác vụ (`TARGET_CRAWL`, `SINGLE_CRAWL`, `DOWNLOAD`) trên trang Lịch sử chạy với thời gian bắt đầu, kết thúc, tổng thời lượng thực thi (`duration_ms`), loại kích hoạt, đầu vào, kết quả và lỗi; có thể lọc đa tiêu chí, bấm Chạy lại (`Retry`) cho các phiên lỗi/dính Captcha và xóa lịch sử cũ.

**Blocked by:** 04: Công cụ Crawl theo ID / Link Chia Sẻ (Chạy ngay & Hẹn giờ 1 lần); 05: Bộ Thiết lập Hẹn Giờ Trực Quan (Visual Scheduler) & Điều khiển Scheduler; 06: Cấu hình Chống Bot (Anti-Bot & Stealth) & Tự động Dừng khi gặp Captcha.

**Status:** ready-for-agent

- [x] Mọi phiên quét mục tiêu, crawl lẻ theo ID/link và tải media đều ghi nhận bản ghi lịch sử với `job_type`, `trigger_type`, `input_summary`, `payload`, `started_at`, `finished_at` và trả về `duration_ms`.
- [x] `GET /api/logs` hỗ trợ lọc theo `job_type`, `status`, `target_id` và phân trang.
- [x] `POST /api/logs/{log_id}/retry` kích hoạt chạy lại đúng tác vụ gốc (quét mục tiêu, crawl theo ID/link hoặc tải lại media) với `trigger_type = 'RETRY'`.
- [x] `DELETE /api/logs/{log_id}` và `DELETE /api/logs` cho phép xóa từng bản ghi hoặc dọn sạch các bản ghi lịch sử đã hoàn tất.
- [x] Giao diện trang Lịch sử chạy tự động làm mới khi có tác vụ đang chạy, hiển thị đầy đủ thông tin, bộ lọc, nút Chạy lại và nút Dọn lịch sử.
- [x] Kiểm thử tích hợp xác nhận việc ghi nhận lịch sử cho cả 3 loại tác vụ, lọc lịch sử, chạy lại phiên lỗi (`Retry`) và xóa lịch sử.
