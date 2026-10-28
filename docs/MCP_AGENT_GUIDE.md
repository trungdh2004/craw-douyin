# Hướng dẫn Tích hợp MCP Server & Giao việc cho AI Agent (`douyin-crawler-mcp`)

Tài liệu này hướng dẫn cách biến hệ thống **Douyin Crawler** thành công cụ (Tool) cho các AI Agent (Antigravity, Claude Code, Cursor, v.v.) thông qua giao thức **MCP (Model Context Protocol)** hoặc dòng lệnh `uv run douyin-mcp`.

Khi đã kết nối, bạn chỉ cần giao việc bằng ngôn ngữ tự nhiên, ví dụ:
> *"Cào từ khóa `穿搭` lấy 30 bài, sau đó chọn ra 5 video nhiều tim nhất chưa phân tích để đẩy sang Server Phân tích."*

---

## 1. Cấu hình MCP Server cho AI Agent (`mcp_config.json`)

Thêm cấu hình `douyin-crawler` vào file cấu hình MCP của Agent (ví dụ `~/.gemini/antigravity/mcp_config.json`, `.mcp.json` hoặc cấu hình của Claude Desktop / Cursor):

```json
{
  "mcpServers": {
    "douyin-crawler": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/trungdh/dev/tools/douyin",
        "douyin-mcp"
      ],
      "env": {
        "DOUYIN_CRAWLER_URL": "http://127.0.0.1:8080",
        "DOUYIN_ADMIN_USERNAME": "admin",
        "DOUYIN_ADMIN_PASSWORD": "admin123"
      }
    }
  }
}
```

> **Lưu ý**: Nếu bạn đã đổi mật khẩu Admin trên giao diện Web (mục **Server Phân tích -> Tài khoản Quản trị**), hãy cập nhật `DOUYIN_ADMIN_USERNAME` và `DOUYIN_ADMIN_PASSWORD` tương ứng trong `env` hoặc trong file `.env` của dự án.

---

## 2. Danh sách 6 Tools mà AI Agent có thể sử dụng

| Tên Tool | Công dụng chính | Tham số quan trọng |
| :--- | :--- | :--- |
| **`crawl_and_send_top_videos`** | **Tự động trọn gói 1 bước**: Cào Kênh/Từ khóa -> Chờ cào xong -> Lọc ra `top_n` video nhiều tim nhất (`digg_count` giảm dần, tự bỏ qua video đã gửi phân tích) -> Tải MP4 không logo -> Gửi sang Server Phân tích. | `target_type` (`KEYWORD` \| `CHANNEL` \| `COLLECT`), `target_value`, `max_crawl_items` (mặc định `30`), `top_n` (mặc định `5`), `exclude_already_analyzed` (mặc định `true`), `min_duration_sec`, `max_duration_sec` |
| **`search_top_videos`** | Tìm kiếm và xếp hạng video đã có trong kho dữ liệu theo số tim (`digg_count`), ngày đăng (`create_time`), hoặc thời lượng (`duration_ms`). | `search`, `target_id`, `top_n` (mặc định `10`), `exclude_already_analyzed`, `only_analyzed`, `min_digg`, `sort` (`digg_count`) |
| **`trigger_crawl`** | Kích hoạt phiên cào Kênh/Từ khóa (`mode="TARGET"`) hoặc danh sách link lẻ (`mode="SINGLE_LINKS"`) và chờ đến khi hoàn tất. | `mode`, `target_type`, `target_value`, `inputs`, `max_crawl_items`, `wait_for_completion` |
| **`send_videos_to_analysis`** | Đẩy danh sách mã `aweme_ids` chỉ định sang Server Phân tích (tự động tải MP4 không logo nếu chưa tải). | `aweme_ids` (mảng ID), `profile` (`"detailed"` \| `"fast"`) |
| **`get_system_status`** | Kiểm tra phiên đăng nhập Douyin (`AUTHENTICATED` / `CAPTCHA_REQUIRED`), chế độ chạy ẩn (`headless_mode`), thống kê kho video và địa chỉ IP:Port của Server Phân tích. | *(Không cần tham số)* |
| **`configure_analysis_server`** | Đổi địa chỉ IP/Hostname và Port của Server Phân tích mà không cần mở giao diện Web. | `host` (ví dụ `"192.168.1.50"`), `port` (ví dụ `8000`) |

---

## 3. Chạy trực tiếp qua CLI (Dành cho Agent dùng Terminal / Bash)

Ngay cả khi Agent không bật MCP, Agent vẫn có thể gọi trực tiếp mọi tool qua lệnh `uv run douyin-mcp`:

```bash
# 1. Xem danh sách toàn bộ tools và schema JSON
uv run douyin-mcp --list-tools

# 2. Kiểm tra trạng thái hệ thống
uv run douyin-mcp --tool get_system_status --args '{}'

# 3. Cào từ khóa "美食" (30 bài) và tự động chọn Top 5 video nhiều tim nhất gửi phân tích
uv run douyin-mcp --tool crawl_and_send_top_videos --args '{
  "target_type": "KEYWORD",
  "target_value": "美食",
  "max_crawl_items": 30,
  "top_n": 5,
  "exclude_already_analyzed": true
}'

# 4. Chỉ lọc Top 3 video nhiều tim nhất đang có sẵn trong kho (chưa gửi phân tích)
uv run douyin-mcp --tool search_top_videos --args '{
  "top_n": 3,
  "exclude_already_analyzed": true,
  "sort": "digg_count",
  "order": "desc"
}'
```

---

## 4. Các mẫu câu lệnh (Prompt) để bạn giao việc cho AI

Bạn có thể copy hoặc nói trực tiếp với AI Agent các câu lệnh như:

1. **Cào từ khóa mới & gửi Top nhiều tim nhất**:
   > *"Cào từ khóa `穿搭` trên Douyin lấy khoảng 40 video, chọn 5 video nhiều tim nhất (chưa gửi phân tích lần nào) và đẩy sang Server Phân tích giúp tôi."*
2. **Cào từ một Kênh Douyin kèm điều kiện thời lượng**:
   > *"Quét kênh `https://www.douyin.com/user/MS4wLjABAAAA...` lấy 30 bài mới nhất, lọc ra 3 video nhiều tim nhất có thời lượng dưới 60 giây rồi gửi sang phân tích."*
3. **Chọn từ dữ liệu đã cào sẵn trong kho (không cần cào lại)**:
   > *"Tìm trong kho dữ liệu những video chưa phân tích, lấy 5 video nhiều tim nhất và đẩy sang Server Phân tích."*
4. **Đổi địa chỉ Server Phân tích sang máy khác trong mạng LAN**:
   > *"Trỏ Server Phân tích sang IP `192.168.1.120` cổng `8000` rồi gửi 3 video nhiều tim nhất của từ khóa `ootd` sang đó."*
