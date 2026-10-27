#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

uv run alembic upgrade head

BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"
if [[ ! -d frontend/dist ]] && [[ -x "$BUN_BIN" ]]; then
  (cd frontend && "$BUN_BIN" run build)
fi

echo "Dashboard (Vite + shadcn/ui): http://localhost:8080"
echo "Nhấn Ctrl+C để dừng ứng dụng."
exec uv run uvicorn douyin_crawler.main:app --reload --port 8080
