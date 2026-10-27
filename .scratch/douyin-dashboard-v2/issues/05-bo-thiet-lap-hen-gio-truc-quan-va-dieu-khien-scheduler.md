# 05: Bộ Thiết lập Hẹn Giờ Trực Quan (Visual Scheduler) & Điều khiển Scheduler

**What to build:** Người vận hành quản lý các mục tiêu quét (`CHANNEL`, `KEYWORD`, `COLLECT`) qua Modal biểu mẫu trực quan với 4 chế độ hẹn giờ (`INTERVAL` theo chu kỳ phút/giờ, `DAILY` theo giờ cố định và thứ trong tuần, `ONCE` chạy 1 lần đúng ngày giờ, và `CRON` nâng cao), tuỳ chọn tự động tải media khi phát hiện bài mới (`auto_download`), xem thời điểm chạy kế tiếp (`next_run_at`) và tạm dừng / tiếp tục toàn bộ bộ lập lịch.

**Blocked by:** 01: Khung ứng dụng Vite + shadcn/ui Left Sidebar & Trang Tổng Quan Hệ Thống.

**Status:** ready-for-agent

- [x] Mở rộng mục tiêu quét với `schedule_type` (`INTERVAL`, `DAILY`, `ONCE`, `CRON`, `MANUAL`), `schedule_config`, `run_at`, và `auto_download`.
- [x] Bộ lập lịch đăng ký đúng loại trigger tương ứng (`IntervalTrigger`, `CronTrigger`, `DateTrigger`), trả về `next_run_at` cho từng mục tiêu và tự động tắt mục tiêu `ONCE` sau khi chạy xong.
- [x] Khi mục tiêu bật `auto_download = True`, các bài đăng mới phát hiện trong phiên quét mục tiêu đó được tự động đưa vào hàng đợi tải media không logo.
- [x] Bổ sung API `GET /api/scheduler/status`, `POST /api/scheduler/pause` và `POST /api/scheduler/resume` để kiểm soát toàn bộ bộ lập lịch.
- [x] Giao diện trang Mục tiêu & Hẹn giờ cung cấp Modal thêm/sửa trực quan với bộ chọn lịch 4 chế độ, hiển thị `next_run_at` và công tắc Pause/Resume Scheduler.
- [x] Kiểm thử tích hợp xác nhận các chế độ lập lịch (`INTERVAL`, `DAILY`, `ONCE`, `CRON`), `next_run_at`, `auto_download` và thao tác Pause/Resume bộ lập lịch.
