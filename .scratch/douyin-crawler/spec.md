# Hệ thống Crawl Douyin Đặt Lịch & Tải Video Không Logo Theo Yêu Cầu

Status: ready-for-agent

## Problem Statement

Việc thu thập dữ liệu từ Douyin (theo kênh sáng tạo và từ khóa tìm kiếm) ở quy mô cá nhân hoặc đội nhóm nhỏ gặp 3 bài toán thực tế lớn:

1. **Chữ ký chống bot và hết hạn phiên đăng nhập:** API của Douyin yêu cầu các tham số chữ ký phức tạp (`a_bogus`, `X-Bogus`) thường xuyên thay đổi theo mã JS mới và yêu cầu Cookie hợp lệ. Các công cụ chỉ dùng HTTP thuần rất dễ gãy khi Douyin cập nhật thuật toán hoặc bắt người dùng phải copy-paste Cookie thủ công liên tục.
2. **Lãng phí dung lượng ổ cứng nếu tải toàn bộ video tự động:** Nếu cứ mỗi lần chạy lịch đều tải toàn bộ file `.mp4` về máy sẽ gây tốn ổ cứng và băng thông cho những video không có nhu cầu sử dụng; ngược lại nếu chỉ lưu đường dẫn CDN của Douyin vào Database thì chỉ sau vài giờ đến vài ngày, cả ảnh bìa (Cover) lẫn link tải Video đều bị hết hạn chữ ký (`403 Forbidden`).
3. **Quét trùng lặp toàn bộ kênh mỗi lần chạy lịch:** Nếu không có cơ chế nhận diện các bài ghim đầu kênh (tối đa 3 bài ghim) và tự động dừng cuộn trang ngay khi gặp các bài cũ đã lưu trong Database, mỗi lần chạy lịch sẽ quét lại hàng trăm video cũ, gây tốn thời gian và dễ kích hoạt Captcha kéo hình của Douyin.

## Solution

Xây dựng hệ thống thu thập và quản lý dữ liệu Douyin chuyên biệt dựa trên **Persistent Chromium Profile (Playwright / CDP)** (chắt lọc phần lõi Douyin từ `MediaCrawler`), kết hợp với **PostgreSQL**, **APScheduler**, và **FastAPI Web Dashboard** theo quy trình 2 pha:

1. **Giữ phiên trình duyệt thật (Persistent Browser Session):** Người dùng chỉ cần bấm mở trình duyệt trên máy và quét mã QR đăng nhập Douyin 1 lần. Toàn bộ trạng thái phiên được lưu cố định vào thư mục profile để các lần chạy lịch tự động sau tái sử dụng, bắt trực tiếp gói tin JSON từ API nội bộ của Douyin mà không lo gãy chữ ký `a_bogus`.
2. **Quy trình thu thập & tải Media 2 pha (Crawl Metadata + Cover theo lịch, Bấm nút mới tải Video):**
   - **Pha 1 (Chạy theo lịch - Scheduled Crawl):** Quét các kênh hoặc từ khóa theo cấu hình Cron, chống trùng lặp thông minh (bỏ qua tối đa 3 bài ghim ở đầu kênh nếu đã có trong DB và dừng cuộn ngay khi gặp các bài thường đã lưu), lưu đầy đủ Metadata vào PostgreSQL, và **chỉ tải sẵn file Ảnh bìa (Cover nhẹ ~30KB)** về ổ cứng để giao diện Web không bao giờ bị lỗi ảnh chết link. Mặc định bỏ qua phần quét bình luận để tốc độ nhanh gấp 5–10 lần và tránh dính Captcha.
   - **Pha 2 (Tải Video theo yêu cầu - On-Demand Download):** Trên giao diện Web Dashboard, người dùng duyệt danh sách video qua ảnh bìa, lọc theo kênh/từ khóa/trạng thái tải, sắp xếp theo lượt tim/share/comment/lưu hoặc ngày đăng. Chỉ khi người dùng bấm nút **"Lưu Video"** trên video nào thì hệ thống mới tải file video gốc không logo (hoặc bộ ảnh nếu là bài trượt ảnh) về ổ cứng theo cấu trúc `{ten_kenh}/{YYYY-MM-DD}/{aweme_id}`. Nếu link CDN đã lưu bị hết hạn (`403 Forbidden`), hệ thống tự động dùng `aweme_id` lấy lại link mới từ Douyin rồi tải về.

## User Stories

1. Là người vận hành, tôi muốn mở cửa sổ trình duyệt Chromium trực tiếp từ Dashboard để quét mã QR đăng nhập Douyin 1 lần, nhằm mục đích lưu giữ phiên đăng nhập và Cookie cho toàn bộ các lần chạy lịch tự động về sau.
2. Là người vận hành, tôi muốn xem trạng thái phiên đăng nhập hiện tại trên Dashboard, nhằm mục đích biết được trình duyệt đang sẵn sàng hay cần quét lại QR.
3. Là người vận hành, tôi muốn thêm mục tiêu quét theo Kênh Douyin (bằng link kênh hoặc `sec_uid`) kèm biểu thức lịch chạy Cron, nhằm mục đích tự động thu thập bài đăng mới của kênh đó định kỳ.
4. Là người vận hành, tôi muốn thêm mục tiêu quét theo Từ khóa tìm kiếm kèm lịch chạy Cron và giới hạn số bài tối đa mỗi lần quét, nhằm mục đích tự động thu thập các video xu hướng theo chủ đề quan tâm.
5. Là người vận hành, tôi muốn bật/tắt, chỉnh sửa hoặc xóa bất kỳ mục tiêu quét nào ngay trên giao diện Web, nhằm mục đích chủ động kiểm soát các luồng thu thập.
6. Là người vận hành, tôi muốn bấm nút "Chạy quét ngay" (Run Now) cho bất kỳ mục tiêu nào, nhằm mục đích kiểm tra kết quả tức thì mà không phải chờ tới giờ chạy lịch tiếp theo.
7. Là người vận hành, tôi muốn bộ quét kênh tự động nhận diện và bỏ qua tối đa 3 bài ghim ở đầu kênh (`is_top = 1`) nếu các bài đó đã có trong Database, nhằm mục đích không bị dừng quét sớm do gặp bài ghim cũ.
8. Là người vận hành, tôi muốn bộ quét kênh tự động dừng cuộn trang ngay khi gặp liên tiếp các bài đăng thường (`is_top = 0`) đã tồn tại trong PostgreSQL, nhằm mục đích rút ngắn thời gian chạy lịch và giảm số lượng request lên Douyin.
9. Là người vận hành, tôi muốn hệ thống trích xuất và lưu đầy đủ Metadata của bài đăng (`aweme_id`, loại bài Video/Album ảnh, tiêu đề/mô tả, danh sách hashtag, thời gian đăng, `sec_uid` tác giả, tên kênh, avatar kênh, số lượt tim, bình luận, chia sẻ, lưu/bookmark, và URL media gốc không logo) vào PostgreSQL, nhằm mục đích tra cứu và phân tích lâu dài.
10. Là người vận hành, tôi muốn hệ thống mặc định bỏ qua việc quét danh sách bình luận chi tiết trong các phiên chạy lịch, nhằm mục đích tăng tốc độ thu thập gấp 5–10 lần và hạn chế tối đa việc bị Douyin chặn Captcha.
11. Là người vận hành, tôi muốn hệ thống tự động tải và lưu bản sao Ảnh bìa (Cover ~30KB) của mỗi bài đăng mới về ổ cứng ngay trong lúc chạy lịch, nhằm mục đích giữ cho ảnh hiển thị trên Web Dashboard luôn sống vĩnh viễn kể cả khi link ảnh của Douyin hết hạn sau vài ngày.
12. Là người vận hành, tôi muốn hệ thống KHÔNG tự động tải file video `.mp4` nặng trong lúc chạy lịch, nhằm mục đích tiết kiệm dung lượng ổ cứng và băng thông mạng.
13. Là người vận hành, tôi muốn duyệt toàn bộ các bài đăng đã thu thập trên giao diện Thư viện Video (hiển thị ảnh bìa local, mô tả, tên kênh, ngày đăng, số tim/comment/share/bookmark, nguồn quét, và trạng thái tải), nhằm mục đích đánh giá nhanh nội dung nào đáng lưu trữ.
14. Là người vận hành, tôi muốn lọc danh sách video theo nguồn quét (kênh hoặc từ khóa cụ thể), loại bài đăng (video hoặc album ảnh), khoảng thời gian đăng, số lượt tim tối thiểu, từ khóa trong mô tả, và trạng thái tải (`NONE`, `DOWNLOADING`, `COMPLETED`, `FAILED`), nhằm mục đích nhanh chóng tìm ra các video chất lượng cao.
15. Là người vận hành, tôi muốn sắp xếp danh sách video theo ngày đăng, ngày thu thập, số lượt tim, số lượt chia sẻ, số lượt bình luận, hoặc số lượt lưu, nhằm mục đích phát hiện ngay các video đang viral nhất.
16. Là người vận hành, tôi muốn xem trước (preview) hoặc mở link gốc Douyin của bài đăng ngay từ thẻ video trên Web, nhằm mục đích kiểm tra nội dung trước khi quyết định lưu về ổ cứng.
17. Là người vận hành, tôi muốn bấm nút "Lưu Video" trên từng bài đăng để hệ thống chạy ngầm việc tải file video không logo (hoặc trọn bộ ảnh gốc nếu là bài trượt ảnh) về ổ cứng theo thư mục `{ten_kenh}/{YYYY-MM-DD}/{aweme_id}`, nhằm mục đích chỉ lưu trữ những video tôi đã chọn lọc.
18. Là người vận hành, tôi muốn chọn nhiều bài đăng cùng lúc trên giao diện và bấm tải hàng loạt (Batch Download), nhằm mục đích tiết kiệm thao tác khi duyệt nhiều video hay.
19. Là người vận hành, tôi muốn bộ tải video tự động phát hiện khi link CDN đã lưu trong DB bị hết hạn (`403 Forbidden` hoặc quá thời gian `x-expires`) và tự động lấy lại link không logo mới thông qua `aweme_id` trước khi tải, nhằm mục đích đảm bảo nút "Lưu Video" luôn hoạt động thành công kể cả với các bài đã crawl từ nhiều tuần trước.
20. Là người vận hành, tôi muốn theo dõi trạng thái tải trực quan (`NONE` -> `DOWNLOADING` -> `COMPLETED` / `FAILED`) và đường dẫn file trên ổ cứng ngay tại thẻ video, nhằm mục đích biết chính xác file nào đã tải xong.
21. Là người vận hành, tôi muốn xem lịch sử các lần chạy quét (thời gian bắt đầu, kết thúc, tên mục tiêu, số bài mới phát hiện, số bài cập nhật, trạng thái thành công hay lỗi), nhằm mục đích giám sát độ ổn định của bộ lập lịch.
22. Là người vận hành, tôi muốn khởi chạy PostgreSQL dễ dàng qua `docker-compose.yml` và chạy toàn bộ Backend + Scheduler + Giao diện Web chỉ trong 1 tiến trình FastAPI duy nhất, nhằm mục đích đơn giản hóa việc cài đặt và vận hành trên PC hoặc Server.

## Implementation Decisions

### 1. Kiến trúc tổng thể & Phân tách Module
- **Dịch vụ hợp nhất (Single Unified Service):** Ứng dụng chạy dưới dạng một tiến trình FastAPI duy nhất, vừa cung cấp REST API, vừa phục vụ giao diện Web Dashboard (HTML5 + TailwindCSS + Alpine.js), đồng thời quản lý vòng đời của bộ lập lịch `APScheduler` (`AsyncIOScheduler`).
- **Tách riêng lõi Douyin từ `MediaCrawler`:** Loại bỏ hoàn toàn 6 nền tảng mạng xã hội không dùng đến trong `MediaCrawler` gốc, chỉ giữ và chuẩn hóa 3 thành phần chuyên biệt cho Douyin:
  - **Browser Session Manager:** Quản lý Playwright Chromium Persistent Context lưu trên ổ cứng. Hỗ trợ chế độ hiển thị giao diện (để quét QR đăng nhập / giải Captcha khi cần) và chế độ chạy tự động cho các tác vụ ngầm. Sử dụng khóa bất đồng bộ (`asyncio.Lock`) để đảm bảo tại một thời điểm không có 2 tiến trình xung đột trên cùng một thư mục Chrome Profile.
  - **Douyin Scraper Engine:** Điều khiển trình duyệt truy cập trang kênh hoặc trang tìm kiếm, bắt trực tiếp các gói tin phản hồi JSON của Douyin (`/aweme/v1/web/aweme/post/`, `/aweme/v1/web/general/search/single/`, `/aweme/v1/web/aweme/detail/`), chuẩn hóa dữ liệu và áp dụng thuật toán dừng quét thông minh (Incremental Stop).
  - **Media Downloader Service:** Sử dụng `httpx.AsyncClient` kèm header/cookie chuẩn để:
    1. Tải ảnh bìa nhẹ (`~30KB`) lưu vào thư mục `covers/` ngay trong lúc crawl.
    2. Tải video `.mp4` không logo (hoặc danh sách ảnh gốc đối với bài đăng dạng Note `aweme_type == 68`) khi người dùng bấm nút Lưu, phân cấp theo `{channel_identifier}/{YYYY-MM-DD}/{aweme_id}.mp4`.
    3. Tự động gọi qua Browser Session Manager để lấy lại chi tiết bài đăng theo `aweme_id` nếu URL tải video trong DB trả về mã lỗi `403` hoặc đã quá hạn `x-expires`.

### 2. Thiết kế Schema Cơ sở dữ liệu (PostgreSQL)

```sql
-- Bảng cấu hình mục tiêu & lịch quét
CREATE TABLE crawl_targets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    target_type VARCHAR(32) NOT NULL, -- 'CHANNEL' | 'KEYWORD'
    target_value TEXT NOT NULL,       -- URL kênh / sec_uid hoặc từ khóa tìm kiếm
    cron_expr VARCHAR(64) NOT NULL DEFAULT '0 */6 * * *',
    max_items_per_run INT NOT NULL DEFAULT 50,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    last_status VARCHAR(32) DEFAULT 'IDLE', -- 'IDLE' | 'RUNNING' | 'SUCCESS' | 'FAILED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Bảng lưu trữ bài đăng Douyin (Metadata + Cover tải sẵn; Video tải khi bấm nút)
CREATE TABLE douyin_videos (
    aweme_id VARCHAR(64) PRIMARY KEY,
    target_id INT REFERENCES crawl_targets(id) ON DELETE SET NULL,
    aweme_type INT NOT NULL DEFAULT 0, -- 0: Video, 68: Album ảnh trượt (Note)
    description TEXT NOT NULL DEFAULT '',
    hashtags JSONB NOT NULL DEFAULT '[]',
    create_time TIMESTAMPTZ NOT NULL,
    author_sec_uid VARCHAR(255) NOT NULL,
    author_nickname VARCHAR(255) NOT NULL,
    author_avatar TEXT,
    digg_count BIGINT NOT NULL DEFAULT 0,
    comment_count BIGINT NOT NULL DEFAULT 0,
    share_count BIGINT NOT NULL DEFAULT 0,
    collect_count BIGINT NOT NULL DEFAULT 0,
    cover_remote_url TEXT,
    cover_local_path TEXT,
    raw_video_url TEXT,
    image_urls JSONB NOT NULL DEFAULT '[]',
    download_status VARCHAR(32) NOT NULL DEFAULT 'NONE', -- 'NONE' | 'DOWNLOADING' | 'COMPLETED' | 'FAILED'
    video_local_path TEXT,
    download_error TEXT,
    downloaded_at TIMESTAMPTZ,
    crawled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Bảng lịch sử các phiên chạy quét
CREATE TABLE crawl_logs (
    id SERIAL PRIMARY KEY,
    target_id INT REFERENCES crawl_targets(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL, -- 'RUNNING' | 'SUCCESS' | 'FAILED'
    new_videos_count INT NOT NULL DEFAULT 0,
    updated_videos_count INT NOT NULL DEFAULT 0,
    error_message TEXT
);
```

### 3. Logic Quét Thông Minh (Incremental Crawling) & Chống Trùng Lặp
- Khi quét mục tiêu loại `CHANNEL`:
  - Mỗi bài đăng trong JSON trả về từ `/aweme/v1/web/aweme/post/` có trường `is_top` (`1` là bài ghim đầu kênh, `0` là bài đăng thường theo thứ tự thời gian giảm dần).
  - Nếu `is_top == 1` và `aweme_id` đã tồn tại trong bảng `douyin_videos`: cập nhật lại các chỉ số tương tác (`digg_count`, `comment_count`, `share_count`, `collect_count`) và bỏ qua không cộng vào bộ đếm dừng.
  - Nếu `is_top == 0` và `aweme_id` đã tồn tại trong bảng `douyin_videos`: tăng biến đếm `consecutive_existing_count`. Ngay khi `consecutive_existing_count >= 3` (hoặc tổng số bài quét trong phiên đạt `max_items_per_run`), lập tức dừng cuộn trang và kết thúc phiên quét.

### 4. Giao kèo REST API (API Contracts)
- `GET /api/targets` / `POST /api/targets` / `PUT /api/targets/{id}` / `DELETE /api/targets/{id}`: Thêm/sửa/xóa mục tiêu quét và tự động đồng bộ lập lịch với `APScheduler`.
- `POST /api/targets/{id}/run`: Kích hoạt chạy quét ngay lập tức dưới nền cho một mục tiêu.
- `GET /api/videos`: Truy vấn phân trang danh sách bài đăng kèm bộ lọc (`target_id`, `search`, `min_digg`, `download_status`, `aweme_type`, `date_from`, `date_to`) và sắp xếp (`create_time`, `crawled_at`, `digg_count`, `share_count`, `comment_count`, `collect_count`).
- `POST /api/videos/{aweme_id}/download`: Kích hoạt tải theo yêu cầu file video/ảnh không logo về ổ cứng (tự động làm mới link nếu link cũ đã hết hạn).
- `POST /api/videos/batch-download`: Kích hoạt tải hàng loạt cho danh sách nhiều `aweme_id`.
- `GET /api/logs`: Lấy danh sách lịch sử chạy quét gần nhất.
- `GET /api/browser/status` & `POST /api/browser/login`: Kiểm tra trạng thái phiên đăng nhập hoặc mở cửa sổ trình duyệt để quét mã QR Douyin.

## Testing Decisions

- **Triết lý kiểm thử:** Chỉ kiểm thử các hành vi quan sát được từ bên ngoài (trạng thái dữ liệu trong Database, cấu trúc file lưu trên ổ cứng, phản hồi của HTTP API, hành vi dừng quét thông minh khi gặp bài cũ, và cơ chế tự lấy lại link mới khi link tải video hết hạn), tuyệt đối không kiểm thử chi tiết cài đặt nội bộ.
- **Seam kiểm thử duy nhất (Single Primary Testing Seam):**
  - **REST API + Orchestrator Integration Seam:** Toàn bộ bài test gọi qua `AsyncClient` của FastAPI / entrypoint điều phối gắn với Database thật dành cho test, và chỉ thay thế (stub/fake) duy nhất ranh giới giao tiếp mạng ra ngoài với Douyin (`DouyinBrowserAdapter` và bộ tải file HTTP ngoài) bằng dữ liệu JSON mẫu và luồng byte media giả lập.
- **Các kịch bản cốt lõi cần kiểm thử tại Seam này:**
  1. Tạo, cập nhật, bật/tắt và xóa `crawl_targets` qua API lưu đúng vào Database và đồng bộ lịch trong bộ lập lịch.
  2. Chạy quét một kênh có 3 bài ghim (`is_top = 1`) đã nằm sẵn trong DB sẽ bỏ qua 3 bài ghim đó để lấy các bài mới phía sau, chỉ dừng lại khi gặp các bài không ghim (`is_top = 0`) đã tồn tại trong DB; đồng thời tải file ảnh Cover cho bài mới nhưng giữ `download_status = 'NONE'` cho file video.
  3. Lọc và sắp xếp danh sách video qua `GET /api/videos` theo lượt tim, nguồn quét, và trạng thái tải trả về kết quả phân trang chính xác.
  4. Bấm tải video (`POST /api/videos/{aweme_id}/download`) khi `raw_video_url` còn hạn sẽ tải file về đúng cấu trúc thư mục `{ten_kenh}/{YYYY-MM-DD}/{aweme_id}.mp4` và chuyển trạng thái sang `'COMPLETED'`.
  5. Bấm tải video (`POST /api/videos/{aweme_id}/download`) khi `raw_video_url` trả về lỗi `403 Forbidden` (hết hạn chữ ký) sẽ tự động gọi hàm làm mới link theo `aweme_id` rồi tải thành công.

## Out of Scope

- Quét chi tiết danh sách bình luận cấp 1 và cấp 2 (được loại bỏ chủ đích để tối ưu tốc độ chạy lịch và tránh dính Captcha).
- Thu thập dữ liệu của các nền tảng mạng xã hội Trung Quốc khác (Xiaohongshu, Weibo, Bilibili, Kuaishou...).
- Ghi hình luồng Livestream trực tiếp (`flv`/`hls`) và quét dữ liệu giỏ hàng thương mại điện tử Douyin Shop.
- Hệ thống Proxy Pool phân tán hoặc xoay vòng hàng trăm tài khoản (không cần thiết cho quy mô cá nhân/nhóm nhỏ dùng Persistent Browser Profile).
- Tách project Frontend React/Next.js độc lập (giao diện Web được tích hợp trực tiếp trong FastAPI).

## Further Notes

- Khi triển khai thực tế, cơ sở dữ liệu PostgreSQL chạy trong Docker qua `docker-compose.yml`, còn tiến trình FastAPI + Playwright nên chạy trực tiếp trên máy chủ/máy cá nhân (hoặc container có X11/VNC) để khi bấm nút mở trình duyệt đăng nhập QR (`POST /api/browser/login`), cửa sổ Chromium hiển thị trực quan cho người vận hành quét mã.
