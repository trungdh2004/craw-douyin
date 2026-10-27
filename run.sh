#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"

trap 'kill 0' INT TERM EXIT

uv run uvicorn douyin_crawler.main:app --reload --port 8080 &

if [[ -x "$BUN_BIN" ]]; then
  (cd frontend && "$BUN_BIN" run dev -- --port 5173) &
elif command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run dev -- --port 5173) &
fi

echo "Frontend (Vite + shadcn/ui): http://localhost:5173"
echo "Backend API:                 http://localhost:8080"
echo "Nhấn Ctrl+C để dừng ứng dụng."

wait
