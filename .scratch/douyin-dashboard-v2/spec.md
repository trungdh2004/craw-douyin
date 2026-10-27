# Nâng Cấp UI/UX Dashboard (Vite + shadcn/ui), Bookmark, Crawl 1 ID, Hẹn Giờ Trực Quan, Chống Bot & Lịch Sử Chạy Chi Tiết

Status: ready-for-agent

## Problem Statement

Hệ thống Douyin Crawler hiện tại đã có lõi thu thập cơ bản nhưng gặp các hạn chế lớn khi vận hành thực tế:

1. **Giao diện UI/UX sơ sài và thiếu thông tin quan trọng:** Giao diện hiện tại chỉ là một trang HTML đơn giản nhồi nhét tất cả vào một cột dọc, dùng hộp thoại `prompt()` mặc định của trình duyệt để chỉnh sửa, không có thanh điều hướng Sidebar, không có trình phát xem trước (Preview Player) cho video/album ảnh, và danh sách bài đã crawl chưa hiển thị sẵn đầy đủ metadata cũng như thời lượng phát của video (`duration`), thời gian đăng và thời gian thu thập.
2. **Thiếu tính năng quản lý Bookmark (Yêu thích / Lưu trữ chọn lọc):** Người vận hành chưa thể đánh dấu Bookmark (kèm nhãn/ghi chú cá nhân) cho các video tâm đắc ngay trên Dashboard để lọc xem lại hoặc tải hàng loạt, cũng như chưa thể đồng bộ danh sách video Đã lưu (Collect/Favorites) từ chính tài khoản Douyin đang đăng nhập.
3. **Chưa hỗ trợ Crawl lẻ 1 ID / Link chia sẻ:** Khi bắt gặp một hoặc một vài video hay trên Douyin, người vận hành không có công cụ nhập trực tiếp mã `aweme_id` hoặc dán đoạn văn bản chứa link chia sẻ/link rút gọn (`v.douyin.com`) để quét lấy ngay hoặc hẹn giờ tải về mà bắt buộc phải tạo mục tiêu quét cả kênh hoặc từ khóa.
4. **Cài đặt hẹn giờ (Scheduler) khó sử dụng:** Người dùng bị buộc phải tự nhớ và gõ biểu thức Cron 5 trường (`0 */6 * * *`), thiếu các chế độ hẹn giờ trực quan (chạy theo chu kỳ mỗi X phút/giờ, chạy cố định hằng ngày/tuần, hoặc hẹn giờ chạy 1 lần vào thời điểm cụ thể) và không nhìn thấy thời điểm chạy kế tiếp (`Next Run`).
5. **Thiếu cơ chế cấu hình Chống Bot (Anti-Bot & Stealth):** Bộ quét hiện cuộn trang với tốc độ cố định (`800ms`), chưa có độ trễ ngẫu nhiên (Random Jitter), chưa ẩn dấu vết tự động hóa WebDriver, chưa có khoảng nghỉ giữa các phiên quét liên tiếp và chưa tự động phát hiện/dừng an toàn khi Douyin bật Captcha kéo hình.
6. **Lịch sử chạy (Execution History) quá đơn giản:** Chỉ in ra các dòng chữ thô cho các lần quét kênh/từ khóa, không theo dõi được tiến trình của các lần Crawl 1 ID hay Tải Media, thiếu thời lượng thực thi (Duration), nguồn kích hoạt, bộ lọc, nút Chạy lại (Retry) khi lỗi và nút dọn dẹp lịch sử cũ.

## Solution

Nâng cấp toàn diện hệ thống theo kiến trúc tách biệt **Frontend SPA hiện đại (Vite + React + TypeScript + TailwindCSS + shadcn/ui)** với bố cục **Left Sidebar Dashboard** kết hợp cùng **FastAPI Backend** mở rộng:

1. **Left Sidebar Dashboard (Vite + shadcn/ui):** Thiết kế giao diện chuyên nghiệp với thanh điều hướng cố định bên trái gồm 7 phân khu: *Tổng quan*, *Thư viện Video*, *Đã Bookmark*, *Crawl theo ID / Link*, *Mục tiêu & Hẹn giờ*, *Lịch sử chạy*, và *Cấu hình Chống Bot*, kèm thanh trạng thái toàn cục (hiển thị phiên đăng nhập Douyin, cảnh báo Captcha, số tác vụ đang chạy và công tắc Scheduler).
2. **Thư viện Video giàu Metadata & Thời gian + Xem trước trực tiếp:**
   - Hiển thị sẵn trên từng mục (hỗ trợ cả chế độ Lưới `Grid View` và Bảng `Table View`): Ảnh bìa kèm badge **thời lượng video (`MM:SS`)** hoặc số lượng ảnh của Album, thời gian đăng bài (`create_time`), thời gian hệ thống crawl (`crawled_at`), mã `aweme_id`, thông tin tác giả (Avatar, Nickname, `sec_uid`), mô tả, danh sách `#hashtag`, nhạc nền (`music_title`, `music_author`), độ phân giải (`width x height`), 4 chỉ số tương tác (Tim, Bình luận, Chia sẻ, Lượt lưu), nguồn quét, trạng thái Bookmark và trạng thái tải file.
   - Bấm vào bài đăng mở **Modal Xem Trước (`shadcn Dialog`)** phát trực tiếp video `.mp4` hoặc trình chiếu bộ ảnh trượt (Carousel).
3. **Hệ thống Bookmark Kép (Dashboard Bookmark + Đồng bộ Douyin Collect):**
   - Cho phép bấm gắn sao/Bookmark bất kỳ bài đăng nào trên Dashboard, gắn nhãn bộ sưu tập (`bookmark_collection`) và ghi chú cá nhân (`bookmark_note`), duyệt riêng trong mục *Đã Bookmark* và tải hàng loạt.
   - Bổ sung loại mục tiêu quét `COLLECT` để tự động thu thập các video trong tab "Đã lưu / Yêu thích" của tài khoản Douyin đang đăng nhập và tự động đánh dấu Bookmark khi lưu vào hệ thống.
4. **Công cụ Crawl theo ID / Link (Quét lẻ & Theo lô):**
   - Cho phép nhập một hoặc nhiều `aweme_id`, link đầy đủ (`douyin.com/video/...`, `/note/...`) hoặc đoạn văn bản chia sẻ chứa link rút gọn (`v.douyin.com/...`).
   - Hỗ trợ chọn **Chạy ngay** hoặc **Hẹn giờ chạy 1 lần (`run_at`)**, kèm công tắc **Tự động tải luôn file Video/Album không logo**.
5. **Bộ thiết lập Hẹn Giờ Trực Quan (Visual Scheduler):**
   - Hỗ trợ 4 chế độ lập lịch: *Theo chu kỳ (`INTERVAL` - mỗi X phút/giờ)*, *Hằng ngày / Hằng tuần (`DAILY` - chọn giờ phút và các thứ trong tuần)*, *Chạy 1 lần (`ONCE` - chọn ngày giờ cụ thể)*, và *Biểu thức Cron nâng cao (`CRON`)*.
   - Hiển thị rõ thời gian chạy tiếp theo (`next_run_at`) và công tắc Tạm dừng / Tiếp tục toàn bộ bộ lập lịch.
6. **Cấu hình Chống Bot (Anti-Bot & Stealth Settings):**
   - Lưu trữ cấu hình chống bot trong cơ sở dữ liệu với 3 Preset (*An toàn cao*, *Cân bằng*, *Tốc độ nhanh*) và cho phép tuỳ chỉnh chi tiết: khoảng trễ ngẫu nhiên khi cuộn trang, khoảng trễ khi tải media, thời gian nghỉ giữa 2 mục tiêu liên tiếp (Cooldown), chế độ Stealth ẩn WebDriver, cuộn trang ngẫu nhiên như người thật, cấu hình Proxy, và cơ chế tự động dừng khi phát hiện Captcha kèm nút mở Chromium để người dùng giải Captcha.
7. **Lịch sử chạy chi tiết (Execution History):**
   - Ghi nhận toàn bộ các phiên thực thi (Scheduled Crawl, Manual Crawl, Crawl 1 ID, Download Media) với thời gian bắt đầu, kết thúc, tổng thời gian chạy (Duration), loại kích hoạt, số bài mới/cập nhật, thông báo lỗi, bộ lọc đa tiêu chí, nút **Chạy lại (Retry)** cho phiên thất bại và nút **Xóa lịch sử**.

## User Stories

1. Là người vận hành, tôi muốn giao diện quản trị được xây dựng bằng Vite, React, TypeScript và `shadcn/ui` với thanh **Left Sidebar cố định bên trái**, nhằm mục đích chuyển đổi mượt mà giữa các phân khu chức năng mà không phải cuộn một trang dài.
2. Là người vận hành, tôi muốn nhìn thấy ngay trên Sidebar/Topbar trạng thái phiên đăng nhập Douyin (`AUTHENTICATED`, `LOGIN_REQUIRED`, `LOGIN_IN_PROGRESS`, `CAPTCHA_REQUIRED`), số tác vụ đang chạy ngầm và trạng thái hoạt động của bộ lập lịch, nhằm mục đích nắm bắt sức khỏe hệ thống tức thời.
3. Là người vận hành, tôi muốn xem bảng Tổng quan (Overview) hiển thị các chỉ số thống kê (tổng số video đã thu thập, số video đã tải về máy, số video đã Bookmark, số mục tiêu đang hẹn giờ, tỷ lệ chạy thành công), nhằm mục đích theo dõi quy mô dữ liệu nhanh chóng.
4. Là người vận hành, tôi muốn mỗi thẻ bài đăng trong danh sách đã crawl hiển thị sẵn **thời lượng của video** theo định dạng `MM:SS` (ví dụ `01:25`) ngay trên góc ảnh bìa (hoặc số lượng ảnh `📷 N ảnh` nếu là Album), nhằm mục đích biết ngay độ dài video trước khi xem hoặc tải.
5. Là người vận hành, tôi muốn nhìn thấy sẵn đầy đủ **Metadata** của bài đăng ngay trên danh sách đã crawl (bao gồm `aweme_id`, tên kênh, avatar, `sec_uid`, thời gian đăng bài `create_time`, thời gian hệ thống thu thập `crawled_at`, mô tả, danh sách `#hashtag`, tên nhạc nền, độ phân giải, 4 chỉ số Tim/Bình luận/Chia sẻ/Lưu, nguồn quét và trạng thái tải), nhằm mục đích đánh giá toàn diện từng video mà không cần bấm vào từng trang lẻ.
6. Là người vận hành, tôi muốn chuyển đổi linh hoạt giữa chế độ xem **Lưới thẻ (`Grid View`)** và **Bảng chi tiết (`Table View`)** trong Thư viện Video và trang Đã Bookmark, nhằm mục đích vừa có thể duyệt trực quan qua ảnh bìa lớn, vừa có thể đối chiếu nhiều cột metadata cùng lúc.
7. Là người vận hành, tôi muốn lọc và sắp xếp danh sách video theo thời lượng video (tối thiểu/tối đa), lượt tim, bình luận, chia sẻ, lượt lưu, ngày đăng, ngày crawl, nguồn quét, loại bài đăng (Video/Album), trạng thái tải và trạng thái Bookmark, nhằm mục đích tìm kiếm chính xác nhóm nội dung cần khai thác.
8. Là người vận hành, tôi muốn bấm vào bất kỳ bài đăng nào trong danh sách để mở **Modal Xem Trước (`shadcn Dialog`)** phát trực tiếp video `.mp4` hoặc lướt xem trọn bộ ảnh Album kèm đầy đủ thông tin metadata và nút copy nhanh `aweme_id` / link gốc / đường dẫn file trên ổ cứng, nhằm mục đích kiểm duyệt nội dung ngay trên Dashboard.
9. Là người vận hành, tôi muốn bấm nút **Bookmark (Gắn sao)** trên bất kỳ bài đăng nào ngay tại Thư viện hoặc Modal xem trước để lưu vào danh sách **Đã Bookmark**, nhằm mục đích đánh dấu các video hay cần tham khảo hoặc tải sau.
10. Là người vận hành, tôi muốn gắn **Nhãn phân loại (`bookmark_collection`)** và **Ghi chú cá nhân (`bookmark_note`)** cho từng video đã Bookmark, đồng thời lọc theo nhãn phân loại trong trang Đã Bookmark, nhằm mục đích tổ chức kho ý tưởng theo chủ đề.
11. Là người vận hành, tôi muốn chọn nhiều bài đăng trong mục Đã Bookmark (hoặc Thư viện) để bấm **Tải hàng loạt** hoặc **Gắn/Bỏ Bookmark hàng loạt**, nhằm mục đích tiết kiệm thời gian thao tác.
12. Là người vận hành, tôi muốn tạo mục tiêu quét loại **Đã lưu trên Douyin (`COLLECT`)** hoặc bấm nút **"Đồng bộ Bookmark từ Douyin"**, để hệ thống tự động quét tab Yêu thích/Đã lưu của tài khoản Douyin đang đăng nhập và đưa toàn bộ bài mới về mục Đã Bookmark trên Dashboard.
13. Là người vận hành, tôi muốn có màn hình **Crawl theo ID / Link** cho phép nhập mã `aweme_id`, link đầy đủ (`douyin.com/video/...`, `douyin.com/note/...`) hoặc dán nguyên đoạn văn bản chia sẻ từ app Douyin có chứa link rút gọn (`v.douyin.com/...`), nhằm mục đích thu thập nhanh các bài đăng cụ thể mà không cần tự tách mã ID thủ công.
14. Là người vận hành, tôi muốn nhập nhiều ID hoặc link (mỗi dòng một mục) vào công cụ Crawl theo ID / Link, nhằm mục đích quét hàng loạt các bài lẻ trong một lần gửi.
15. Là người vận hành, tôi muốn tuỳ chọn **Tự động tải luôn file Video/Album không logo** và **Tự động gắn Bookmark** ngay khi tạo lệnh Crawl theo ID / Link, nhằm mục đích hoàn tất cả việc lấy metadata lẫn tải file chỉ trong 1 bước.
16. Là người vận hành, tôi muốn chọn chế độ **Chạy ngay lập tức** hoặc **Hẹn giờ chạy vào ngày giờ cụ thể (`run_at`)** cho lệnh Crawl theo ID / Link, nhằm mục đích chủ động sắp xếp thời điểm tải dữ liệu.
17. Là người vận hành, tôi muốn thêm và chỉnh sửa mục tiêu quét (`CHANNEL`, `KEYWORD`, `COLLECT`) thông qua một **Modal/Drawer biểu mẫu (`shadcn Dialog`)** đầy đủ trường thông tin thay vì hộp thoại `prompt()` thô sơ, nhằm mục đích thao tác dễ dàng và chính xác.
18. Là người vận hành, tôi muốn thiết lập lịch hẹn giờ bằng bộ chọn trực quan với 4 chế độ: **Theo chu kỳ (Mỗi X phút / X giờ)**, **Hằng ngày / Hằng tuần (chọn giờ cố định và các ngày trong tuần)**, **Hẹn giờ chạy 1 lần (chọn ngày giờ cụ thể)**, hoặc **Nhập biểu thức Cron nâng cao**, nhằm mục đích lên lịch dễ dàng mà không cần nhớ cú pháp Cron.
19. Là người vận hành, tôi muốn xem **Thời gian chạy tiếp theo (`next_run_at`)** của từng mục tiêu hẹn giờ và có thể **Tạm dừng / Tiếp tục (Pause / Resume)** toàn bộ bộ lập lịch chỉ bằng 1 nút bấm, nhằm mục đích kiểm soát hoàn toàn lịch trình tự động.
20. Là người vận hành, tôi muốn thiết lập tùy chọn **"Tự động tải luôn Video/Album khi tìm thấy bài mới"** (`auto_download`) trên từng mục tiêu hẹn giờ nếu muốn kênh quan trọng nào có bài mới là tải sẵn về máy.
21. Là người vận hành, tôi muốn truy cập trang **Cấu hình Chống Bot (Anti-Bot Settings)** để chọn nhanh 1 trong 3 Preset (*An toàn cao*, *Cân bằng*, *Tốc độ nhanh*) hoặc tự điều chỉnh khoảng trễ ngẫu nhiên khi cuộn trang (`scroll_delay_min_ms` – `scroll_delay_max_ms`), khoảng trễ giữa các lần tải media (`download_delay_min_ms` – `download_delay_max_ms`), và thời gian nghỉ giữa 2 phiên quét liên tiếp (`cooldown_between_targets_sec`), nhằm mục đích giảm thiểu nguy cơ bị Douyin chặn.
22. Là người vận hành, tôi muốn bật/tắt chế độ **Stealth ẩn WebDriver**, **Cuộn trang ngẫu nhiên theo nhịp người dùng thật (Human-like Scroll)** và cấu hình **Proxy URL (HTTP/SOCKS5)** trong trang Chống Bot, nhằm mục đích bảo vệ tài khoản và IP khi quét lâu dài.
23. Là người vận hành, tôi muốn hệ thống tự động phát hiện khi Douyin hiển thị Captcha / yêu cầu xác thực trong lúc quét để lập tức dừng phiên quét an toàn, chuyển trạng thái sang `CAPTCHA_REQUIRED`, hiển thị cảnh báo nổi bật trên Dashboard và cho phép tôi bấm **"Mở Chromium giải Captcha"** ngay lập tức.
24. Là người vận hành, tôi muốn xem trang **Lịch sử chạy (Execution History)** hiển thị đầy đủ các phiên chạy (Quét theo lịch, Quét thủ công, Crawl theo ID/Link, Tải Media) kèm thời điểm bắt đầu, thời điểm kết thúc, **tổng thời gian chạy (`duration_ms`)**, nguồn kích hoạt, số bài mới, số bài cập nhật, trạng thái và chi tiết lỗi.
25. Là người vận hành, tôi muốn lọc Lịch sử chạy theo loại tác vụ (`TARGET_CRAWL`, `SINGLE_CRAWL`, `DOWNLOAD`), theo mục tiêu, theo trạng thái (`RUNNING`, `SUCCESS`, `FAILED`, `CAPTCHA_BLOCKED`) và bấm nút **Chạy lại (Retry)** ngay trên một dòng lịch sử bị lỗi hoặc bấm **Xóa lịch sử cũ**, nhằm mục đích vận hành và xử lý sự cố nhanh gọn.

## Implementation Decisions

### 1. Kiến trúc Frontend (Vite + React + TypeScript + TailwindCSS + shadcn/ui)
- **Tách ứng dụng Frontend độc lập tại thư mục `frontend/`:**
  - Sử dụng Vite + React + TypeScript + TailwindCSS kết hợp hệ thống component chuẩn `shadcn/ui` (Dialog, Sheet, DropdownMenu, Select, Tabs, Badge, Switch, Slider, Table, Tooltip, Card, Input, Button, Sonner/Toast).
  - Bố cục khung ứng dụng dùng **Left Sidebar cố định bên trái** + **Header trạng thái toàn cục** + **Vùng nội dung chính** với 7 trang điều hướng:
    1. **Tổng quan (`Overview`):** Thống kê tổng hợp, trạng thái trình duyệt & chống bot, danh sách tác vụ đang chạy và các bài đăng mới nhất.
    2. **Thư viện Video (`Library`):** Thanh công cụ lọc/sắp xếp đa tiêu chí, nút chuyển đổi `Grid View` / `Table View`, hiển thị đầy đủ Metadata + Thời lượng video (`MM:SS`) + Thời gian đăng/crawl, nút Bookmark, chọn nhiều để tải/bookmark hàng loạt, và Modal xem trước (Preview Player).
    3. **Đã Bookmark (`Bookmarks`):** Quản lý các bài đăng đã đánh dấu Bookmark, lọc theo nhãn bộ sưu tập (`bookmark_collection`), chỉnh sửa ghi chú (`bookmark_note`), nút **Đồng bộ mục Đã lưu từ Douyin**, và tải hàng loạt.
    4. **Crawl theo ID / Link (`SingleCrawl`):** Ô nhập 1 hoặc nhiều dòng `aweme_id` / URL / văn bản chia sẻ `v.douyin.com`, chọn chạy ngay hoặc hẹn giờ 1 lần (`run_at`), công tắc tự động tải media và tự động Bookmark, kèm bảng kết quả các lần crawl lẻ gần nhất.
    5. **Mục tiêu & Hẹn giờ (`Targets`):** Bảng danh sách mục tiêu (`CHANNEL`, `KEYWORD`, `COLLECT`), hiển thị chế độ lịch, thời điểm chạy tiếp theo (`next_run_at`), trạng thái lần chạy cuối, và Modal thêm/sửa mục tiêu với **Visual Schedule Picker** (Interval, Hằng ngày/tuần, Chạy 1 lần, Cron nâng cao).
    6. **Lịch sử chạy (`History`):** Bảng lịch sử thực thi chi tiết (auto-refresh khi có tác vụ `RUNNING`), hiển thị thời lượng chạy, bộ lọc theo loại tác vụ/trạng thái/mục tiêu, nút **Chạy lại (Retry)** và **Dọn lịch sử**.
    7. **Cấu hình Chống Bot (`AntiBot`):** Chọn nhanh 3 Preset (*An toàn cao*, *Cân bằng*, *Tốc độ nhanh*) và tinh chỉnh chi tiết các thông số Delay/Jitter, Stealth, Human Scroll, Captcha Auto-Stop, Proxy.
- **Tích hợp Dev & Production:**
  - Trong môi trường phát triển, Vite Dev Server proxy toàn bộ `/api/*` về FastAPI Backend.
  - Khi đã build (`frontend/dist`), FastAPI tự động mount và phục vụ SPA từ đường dẫn gốc `/`.

### 2. Mở rộng Schema Cơ sở dữ liệu (PostgreSQL & Alembic Migration)

```sql
-- 1. Mở rộng bảng crawl_targets để hỗ trợ COLLECT, Visual Schedule, One-time Run và Auto-Download
ALTER TABLE crawl_targets
  DROP CONSTRAINT ck_crawl_targets_type,
  ADD CONSTRAINT ck_crawl_targets_type CHECK (target_type IN ('CHANNEL', 'KEYWORD', 'COLLECT')),
  ADD COLUMN schedule_type VARCHAR(32) NOT NULL DEFAULT 'CRON'
    CHECK (schedule_type IN ('INTERVAL', 'DAILY', 'ONCE', 'CRON', 'MANUAL')),
  ADD COLUMN schedule_config JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN run_at TIMESTAMPTZ,
  ADD COLUMN auto_download BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Mở rộng bảng douyin_videos để lưu Thời lượng video, Metadata mở rộng và Bookmark
ALTER TABLE douyin_videos
  ADD COLUMN duration_ms INT NOT NULL DEFAULT 0,
  ADD COLUMN width INT,
  ADD COLUMN height INT,
  ADD COLUMN music_title VARCHAR(255),
  ADD COLUMN music_author VARCHAR(255),
  ADD COLUMN is_bookmarked BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN bookmarked_at TIMESTAMPTZ,
  ADD COLUMN bookmark_collection VARCHAR(128),
  ADD COLUMN bookmark_note TEXT;

-- 3. Mở rộng bảng crawl_logs để theo dõi mọi loại tác vụ (Target, Crawl 1 ID, Download) và hỗ trợ Retry
ALTER TABLE crawl_logs
  DROP CONSTRAINT ck_crawl_logs_status,
  ADD CONSTRAINT ck_crawl_logs_status CHECK (status IN ('SCHEDULED', 'RUNNING', 'SUCCESS', 'FAILED', 'CAPTCHA_BLOCKED')),
  ADD COLUMN job_type VARCHAR(32) NOT NULL DEFAULT 'TARGET_CRAWL'
    CHECK (job_type IN ('TARGET_CRAWL', 'SINGLE_CRAWL', 'DOWNLOAD')),
  ADD COLUMN trigger_type VARCHAR(32) NOT NULL DEFAULT 'MANUAL'
    CHECK (trigger_type IN ('SCHEDULED', 'MANUAL', 'ONCE', 'RETRY')),
  ADD COLUMN input_summary TEXT,
  ADD COLUMN payload JSONB NOT NULL DEFAULT '{}';

-- 4. Bảng cấu hình Chống Bot (Singleton row id = 1)
CREATE TABLE anti_bot_settings (
  id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  preset VARCHAR(32) NOT NULL DEFAULT 'BALANCED'
    CHECK (preset IN ('SAFE', 'BALANCED', 'FAST', 'CUSTOM')),
  scroll_delay_min_ms INT NOT NULL DEFAULT 1500,
  scroll_delay_max_ms INT NOT NULL DEFAULT 3500,
  download_delay_min_ms INT NOT NULL DEFAULT 500,
  download_delay_max_ms INT NOT NULL DEFAULT 1500,
  cooldown_between_targets_sec INT NOT NULL DEFAULT 10,
  stealth_mode BOOLEAN NOT NULL DEFAULT TRUE,
  human_scroll BOOLEAN NOT NULL DEFAULT TRUE,
  auto_stop_on_captcha BOOLEAN NOT NULL DEFAULT TRUE,
  max_pages_per_run INT NOT NULL DEFAULT 25,
  user_agent TEXT,
  proxy_url TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3. Logic Bóc tách Link / ID & Crawl theo ID / Link (`SingleCrawl`)
- **Trích xuất thông minh (`Identifier Resolver`):**
  - Nếu đầu vào là chuỗi số 15–22 chữ số: nhận diện trực tiếp là `aweme_id`.
  - Nếu đầu vào chứa URL `douyin.com/video/{id}`, `douyin.com/note/{id}`, hoặc tham số `?modal_id={id}`: tách trực tiếp `aweme_id`.
  - Nếu đầu vào là đoạn văn bản chia sẻ từ app Douyin chứa link rút gọn `https://v.douyin.com/...`: trích xuất URL và dùng `MediaHttpAdapter` / HTTP client để phân giải redirect (hoặc mở qua trình duyệt) lấy URL đích chứa `aweme_id`.
- **Thực thi Ngay hoặc Hẹn giờ 1 lần:**
  - Nếu không truyền `run_at` (hoặc `run_at <= now`): tạo bản ghi `CrawlLog(job_type='SINGLE_CRAWL', trigger_type='MANUAL', status='RUNNING')`, gọi `content_adapter.detail(profile, aweme_id)` để lấy đầy đủ `ScrapedPost` (kèm `duration_ms`, `width`, `height`, `music_title`, `music_author`), tải ảnh bìa local, lưu/cập nhật vào `douyin_videos` (đánh dấu `is_bookmarked = True` nếu được yêu cầu), và nếu `auto_download = True` thì kích hoạt luôn `DownloadRunner.start(aweme_id)`.
  - Nếu truyền `run_at > now`: tạo bản ghi `CrawlLog(job_type='SINGLE_CRAWL', trigger_type='ONCE', status='SCHEDULED', payload=...)` và đăng ký `DateTrigger(run_date=run_at)` vào `APScheduler` để tự động chạy khi đến giờ.

### 4. Logic Bộ Lập Lịch Trực Quan (Visual Scheduler)
- Hỗ trợ chuyển đổi cấu hình lịch thân thiện sang trigger của `APScheduler`:
  - `INTERVAL`: dùng `IntervalTrigger(minutes=...)` hoặc quy đổi sang `cron_expr`.
  - `DAILY`: nhận giờ/phút (`hour`, `minute`) và danh sách thứ trong tuần (`days_of_week`, mặc định `*`), sinh `CronTrigger` tương ứng.
  - `ONCE`: nhận mốc thời gian `run_at` (`TIMESTAMPTZ`), dùng `DateTrigger(run_date=run_at)`; sau khi chạy xong tự động chuyển `is_active = False`.
  - `CRON`: dùng trực tiếp `CronTrigger.from_crontab(cron_expr)`.
  - `MANUAL`: chỉ chạy khi bấm nút thủ công, không đăng ký lịch tự động.
- API trả về thêm trường `next_run_at` (lấy từ `job.next_run_time` của `APScheduler`) cho từng mục tiêu và cung cấp endpoint tạm dừng/tiếp tục toàn bộ scheduler.

### 5. Logic Chống Bot (Anti-Bot Engine) & Phát hiện Captcha
- Trong mỗi phiên chạy của `PlaywrightDouyinContentAdapter` và `CrawlRunner`:
  - Đọc cấu hình hiện hành từ bảng `anti_bot_settings`.
  - Khi `stealth_mode = True`: tiêm init script xóa `navigator.webdriver`, giả lập plugin/languages tự nhiên và áp dụng `user_agent` / `proxy_url` nếu có.
  - Khi cuộn trang: nếu `human_scroll = True`, chia nhịp cuộn ngẫu nhiên và nghỉ một khoảng ngẫu nhiên nằm trong `[scroll_delay_min_ms, scroll_delay_max_ms]`.
  - Khi tải nhiều ảnh/video: nghỉ ngẫu nhiên trong `[download_delay_min_ms, download_delay_max_ms]`.
  - Giữa 2 phiên quét mục tiêu liên tiếp: áp dụng khoảng nghỉ `cooldown_between_targets_sec`.
  - Khi phát hiện dấu hiệu Captcha (DOM xuất hiện phần tử xác thực kéo hình của Douyin hoặc gói tin API trả về mã chặn xác thực) và `auto_stop_on_captcha = True`: ném ngoại lệ `CaptchaDetectedError`, dừng phiên quét ngay lập tức, ghi `CrawlLog.status = 'CAPTCHA_BLOCKED'`, cập nhật trạng thái phiên trình duyệt sang `CAPTCHA_REQUIRED`, và cho phép người vận hành bấm mở Chromium hiển thị giao diện để giải Captcha.

### 6. Giao kèo REST API (API Contracts)
- **Tổng quan & Hệ thống:**
  - `GET /api/stats`: Trả về số liệu thống kê tổng quan cho Dashboard (tổng số video, đã tải, đã bookmark, số mục tiêu active, số tác vụ đang chạy, lịch sử gần nhất).
  - `GET /api/scheduler/status`, `POST /api/scheduler/pause`, `POST /api/scheduler/resume`: Kiểm tra trạng thái, tạm dừng và tiếp tục toàn bộ bộ lập lịch.
- **Trình duyệt & Giải Captcha:**
  - `GET /api/browser/status`, `POST /api/browser/login`: Giữ nguyên và bổ sung trạng thái `CAPTCHA_REQUIRED` để mở trình duyệt giải Captcha hoặc đăng nhập lại.
- **Mục tiêu & Hẹn giờ (`/api/targets`):**
  - Mở rộng `POST /api/targets` và `PUT /api/targets/{id}` nhận `target_type` (`CHANNEL` | `KEYWORD` | `COLLECT`), `schedule_type` (`INTERVAL` | `DAILY` | `ONCE` | `CRON` | `MANUAL`), `schedule_config`, `run_at`, `auto_download`.
  - `TargetResponse` trả về thêm `schedule_type`, `schedule_config`, `run_at`, `next_run_at`, `last_run_at`, `auto_download`.
- **Crawl theo ID / Link (`/api/crawl`):**
  - `POST /api/crawl/items`: Nhận `{ inputs: list[str], auto_download: bool, is_bookmarked: bool, bookmark_collection: str | None, run_at: datetime | None }`. Trả về danh sách các tác vụ/bài đăng vừa khởi tạo hoặc hẹn giờ.
- **Thư viện Video, Metadata, Media Streaming & Bookmark (`/api/videos`):**
  - `GET /api/videos`: Bổ sung bộ lọc `is_bookmarked`, `bookmark_collection`, `min_duration_ms`, `max_duration_ms`, và sắp xếp theo `duration_ms`. Mỗi `VideoResponse` trả về đầy đủ `duration_ms`, `width`, `height`, `music_title`, `music_author`, `author_sec_uid`, `author_avatar`, `crawled_at`, `is_bookmarked`, `bookmarked_at`, `bookmark_collection`, `bookmark_note`.
  - `GET /api/videos/{aweme_id}/stream`: Phát trực tiếp file video `.mp4` đã tải về ổ cứng (hoặc danh sách ảnh local đối với bài Album qua `GET /api/videos/{aweme_id}/images/{index}`) để phục vụ Modal Xem Trước.
  - `PATCH /api/videos/{aweme_id}/bookmark`: Bật/tắt `is_bookmarked`, cập nhật `bookmark_collection` và `bookmark_note`.
  - `POST /api/videos/batch-bookmark`: Đánh dấu hoặc bỏ Bookmark hàng loạt cho danh sách `aweme_ids`.
  - `POST /api/bookmarks/sync-douyin`: Kích hoạt quét ngay danh sách Đã lưu (`COLLECT`) từ tài khoản Douyin đang đăng nhập và đánh dấu `is_bookmarked = True`.
- **Cấu hình Chống Bot (`/api/settings/anti-bot`):**
  - `GET /api/settings/anti-bot`: Lấy cấu hình chống bot hiện tại.
  - `PUT /api/settings/anti-bot`: Cập nhật theo Preset (`SAFE` | `BALANCED` | `FAST` | `CUSTOM`) hoặc tuỳ chỉnh từng thông số.
- **Lịch sử chạy (`/api/logs`):**
  - `GET /api/logs`: Hỗ trợ lọc theo `job_type`, `status`, `target_id`, phân trang, trả về thêm `duration_ms`, `job_type`, `trigger_type`, `input_summary`.
  - `POST /api/logs/{log_id}/retry`: Chạy lại một phiên bị lỗi (`FAILED` hoặc `CAPTCHA_BLOCKED`).
  - `DELETE /api/logs`: Xóa một dòng lịch sử hoặc dọn sạch các dòng lịch sử đã hoàn tất.

## Testing Decisions

- **Triết lý kiểm thử:** Chỉ kiểm thử các hành vi quan sát được từ bên ngoài (phản hồi HTTP API, trạng thái lưu trữ trong PostgreSQL, lịch được đăng ký trong Scheduler, file lưu trên đĩa, và luồng xử lý lỗi/Captcha), tuyệt đối không kiểm thử chi tiết cài đặt nội bộ.
- **Seam kiểm thử duy nhất (Single Primary Testing Seam):**
  - Giữ nguyên và tái sử dụng **Seam kiểm thử tích hợp hiện có** tại hàm khởi tạo ứng dụng (`create_app`) kết hợp với `httpx.AsyncClient` và PostgreSQL thật (qua `testcontainers`).
  - Toàn bộ giao tiếp mạng ra ngoài tới Douyin chỉ đi qua 3 cổng giao diện đã có (`DouyinBrowserAdapter`, `DouyinContentAdapter`, `MediaHttpAdapter`). Không tạo thêm bất kỳ seam phụ nào ở tầng service hay repository nội bộ.
- **Các kịch bản cốt lõi được kiểm thử qua Seam này:**
  1. **Metadata mở rộng & Thời lượng video (`duration_ms`) + Streaming:** Khi quét bài đăng mới, `GET /api/videos` trả về đầy đủ `duration_ms`, `width`, `height`, `music_title`, `crawled_at`, `create_time`, hỗ trợ lọc/sắp xếp theo `duration_ms`, và sau khi tải xong có thể phát media qua `GET /api/videos/{aweme_id}/stream`.
  2. **Bookmark nội bộ & Đồng bộ Douyin Collect:** Đánh dấu Bookmark lẻ và hàng loạt kèm nhãn/ghi chú (`PATCH /api/videos/{aweme_id}/bookmark`, `POST /api/videos/batch-bookmark`), lọc `is_bookmarked=true`, và chạy đồng bộ mục Đã lưu từ Douyin (`POST /api/bookmarks/sync-douyin` / mục tiêu `COLLECT`) tự động lưu bài đăng kèm `is_bookmarked = True`.
  3. **Crawl 1 ID / Link chia sẻ & Hẹn giờ 1 lần:** Gửi mã `aweme_id`, link đầy đủ và đoạn văn bản chứa link rút gọn `v.douyin.com` vào `POST /api/crawl/items` (cả chế độ chạy ngay có `auto_download=True` lẫn chế độ hẹn giờ `run_at` trong tương lai).
  4. **Visual Scheduler & Pause/Resume:** Tạo mục tiêu với các chế độ `INTERVAL`, `DAILY`, `ONCE`, `CRON`, kiểm tra `next_run_at` được tính toán chính xác và kiểm tra `POST /api/scheduler/pause` / `resume`.
  5. **Cấu hình Chống Bot & Tự động dừng khi gặp Captcha:** Cập nhật Preset và thông số qua `PUT /api/settings/anti-bot`, kiểm tra khi `DouyinContentAdapter` gặp Captcha thì phiên chạy dừng ngay với trạng thái log `CAPTCHA_BLOCKED` và trạng thái trình duyệt báo `CAPTCHA_REQUIRED`.
  6. **Lịch sử chạy chi tiết, Retry & Dọn dẹp:** Kiểm tra mọi phiên quét mục tiêu, crawl 1 ID và tải video đều ghi nhận đầy đủ `job_type`, `trigger_type`, `duration_ms`; gọi `POST /api/logs/{id}/retry` trên phiên lỗi sẽ kích hoạt chạy lại thành công; gọi `DELETE /api/logs` dọn sạch lịch sử cũ.

## Out of Scope

- Quét chi tiết danh sách bình luận cấp 1 và cấp 2 của bài đăng.
- Hệ thống quản lý đa người dùng (Multi-tenant Authentication / RBAC) trên Dashboard.
- Chỉnh sửa/biên tập cắt ghép video trực tiếp trên trình duyệt.
- Thu thập dữ liệu Livestream hoặc Douyin Shop.

## Further Notes

- Frontend Vite (`frontend/`) sẽ được cấu hình sẵn script build để xuất tĩnh vào `frontend/dist`, giúp người vận hành vừa có thể dùng Vite Dev Server với Hot-Reload khi phát triển, vừa có thể chạy độc lập 1 cổng duy nhất qua FastAPI khi vận hành thực tế.
