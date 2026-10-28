#!/usr/bin/env bash

set -euo pipefail

# Tắt XON/XOFF (Ctrl+S) trên terminal để tránh treo tiến trình uvicorn khi vô tình bấm Ctrl+S
stty -ixon 2>/dev/null || true

cd "$(dirname "$0")"

if [[ "${1:-}" == "login" ]]; then
  if curl -sf -X POST http://localhost:8080/api/browser/login >/dev/null 2>&1; then
    echo "Đã gửi lệnh mở cửa sổ Chromium đăng nhập Douyin qua Backend đang chạy (:8080)."
  else
    uv run python -m douyin_crawler.browser
  fi
  exit 0
fi

BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"

if command -v docker >/dev/null 2>&1; then
  echo "Đang kiểm tra / khởi động PostgreSQL (:5432)..."
  docker compose up -d --wait postgres
fi

trap 'kill 0' INT TERM EXIT

uv run uvicorn douyin_crawler.main:app --reload --reload-dir src --port 8080 &

if [[ -x "$BUN_BIN" ]]; then
  (cd frontend && "$BUN_BIN" run dev -- --port 5173) &
elif command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run dev -- --port 5173) &
fi

echo "Frontend (Vite + shadcn/ui): http://localhost:5173"
echo "Backend API:                 http://localhost:8080"
echo "Nhấn Ctrl+C để dừng ứng dụng."

wait
