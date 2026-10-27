# 06: Cấu hình Chống Bot (Anti-Bot & Stealth) & Tự động Dừng khi gặp Captcha

**What to build:** Người vận hành có thể cấu hình cơ chế chống bot trên trang Cấu hình Chống Bot với 3 Preset (*An toàn cao*, *Cân bằng*, *Tốc độ nhanh*) hoặc tuỳ chỉnh từng thông số (độ trễ ngẫu nhiên khi cuộn và tải, thời gian nghỉ giữa các phiên quét, Stealth ẩn WebDriver, cuộn trang như người thật, Proxy), và hệ thống tự động dừng an toàn khi phát hiện Captcha kèm cảnh báo mở trình duyệt giải Captcha.

**Blocked by:** 01: Khung ứng dụng Vite + shadcn/ui Left Sidebar & Trang Tổng Quan Hệ Thống.

**Status:** ready-for-agent

- [x] Lưu trữ cấu hình chống bot bền vững trong PostgreSQL và cung cấp `GET /api/settings/anti-bot`, `PUT /api/settings/anti-bot` hỗ trợ chọn Preset (`SAFE`, `BALANCED`, `FAST`, `CUSTOM`) cùng các thông số chi tiết.
- [x] Bộ thu thập Playwright và bộ tải media áp dụng cấu hình chống bot hiện hành (Stealth script, Human-like scroll, Random Jitter Delay, Cooldown, Proxy, giới hạn số trang mỗi phiên).
- [x] Khi phát hiện Captcha và bật `auto_stop_on_captcha`, phiên quét dừng ngay lập tức, ghi trạng thái lịch sử `CAPTCHA_BLOCKED`, chuyển trạng thái trình duyệt sang `CAPTCHA_REQUIRED` và hiển thị cảnh báo trên Dashboard để mở trình duyệt giải Captcha.
- [x] Giao diện trang Cấu hình Chống Bot hiển thị thẻ chọn nhanh 3 Preset, các thanh trượt/công tắc cấu hình chi tiết và trạng thái bảo vệ hiện hành.
- [x] Kiểm thử tích hợp xác nhận việc đọc/ghi Preset và thông số chống bot, cũng như hành vi tự động dừng và báo `CAPTCHA_BLOCKED` / `CAPTCHA_REQUIRED` khi gặp Captcha.
