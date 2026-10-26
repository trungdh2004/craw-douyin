# Douyin Crawler

Dịch vụ FastAPI hợp nhất cho việc lên lịch thu thập metadata Douyin và tải media theo yêu cầu.

## Khởi chạy môi trường phát triển

Yêu cầu: Docker, Python 3.12+ và `uv`.

```bash
cp .env.example .env
docker compose up -d postgres
uv sync
uv run playwright install chromium
uv run alembic upgrade head
uv run uvicorn douyin_crawler.main:app --reload
```

Mở Dashboard tại <http://localhost:8000>. Trạng thái dịch vụ có tại <http://localhost:8000/api/health>.

## Kiểm thử

Bộ kiểm thử tích hợp cần Docker để tạo PostgreSQL test dùng một lần:

```bash
uv run pytest
```
