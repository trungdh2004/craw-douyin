#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Lỗi: chưa cài Docker."
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Lỗi: chưa cài uv. Xem https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Đã tạo .env từ .env.example"
fi

echo "Đang khởi chạy PostgreSQL..."
docker compose up -d --wait postgres

echo "Đang cài dependencies..."
uv sync

echo "Đang chuẩn bị Chromium..."
uv run playwright install chromium

echo "Đang cập nhật database..."
uv run alembic upgrade head

echo "Dashboard: http://localhost:8000"
echo "Nhấn Ctrl+C để dừng ứng dụng."
exec uv run uvicorn douyin_crawler.main:app --reload
