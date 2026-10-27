# Douyin Crawler

Hệ thống thu thập metadata Douyin thông minh, quản lý Bookmark, Crawl theo ID/Link, thiết lập Hẹn giờ trực quan, cấu hình Chống Bot (Anti-Bot & Stealth) và tải media không logo theo yêu cầu với giao diện **Left Sidebar Dashboard (Vite + React + TypeScript + TailwindCSS + shadcn/ui)**.

## Khởi chạy môi trường phát triển

Yêu cầu: Docker, Python 3.12+, `uv`, và `bun` (hoặc `npm`).

Cài đặt lần đầu:

```bash
./setup.sh
```

Sau đó chạy ứng dụng:

```bash
./run.sh
```

Mở Dashboard tại <http://localhost:8080>. Trạng thái dịch vụ có tại <http://localhost:8080/api/health>.

Chạy riêng Vite Dev Server với Hot-Reload (proxy `/api` về `:8080`):

```bash
cd frontend && bun run dev
```

## Kiểm thử

Kiểm thử tích hợp Backend (PostgreSQL Testcontainers) & Typecheck:

```bash
uv run pytest
uv run mypy
```

Kiểm thử & Build Frontend (`frontend/`):

```bash
cd frontend && bun run test && bun run build
```
