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

echo "Đang cài dependencies Python..."
uv sync

echo "Đang cài Chromium..."
uv run playwright install chromium

echo "Đang cập nhật database..."
uv run alembic upgrade head

BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"
if [[ -x "$BUN_BIN" ]]; then
  echo "Đang cài đặt và build Frontend (Vite + shadcn/ui)..."
  (cd frontend && "$BUN_BIN" install && "$BUN_BIN" run build)
elif command -v npm >/dev/null 2>&1; then
  echo "Đang cài đặt và build Frontend (Vite + shadcn/ui)..."
  (cd frontend && npm install && npm run build)
fi

echo "Thiết lập hoàn tất. Chạy ./run.sh để mở dự án."
