#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
  echo "Đã tạo .env từ .env.example"
fi

echo "==> 1. Đang kiểm tra & khởi chạy PostgreSQL (Docker)..."
docker compose up -d --wait postgres

echo "==> 2. Đang cập nhật Database schema (Alembic)..."
uv run alembic upgrade head

BUN_BIN="$(command -v bun || echo "$HOME/.bun/bin/bun")"

if [[ "${1:-}" == "--dev" ]]; then
  echo "==> 3. Chế độ DEV: Chạy song song FastAPI Backend (:8080) + Vite Hot-Reload (:5173)..."
  if [[ -x "$BUN_BIN" ]]; then
    (cd frontend && "$BUN_BIN" install)
  elif command -v npm >/dev/null 2>&1; then
    (cd frontend && npm install)
  fi

  trap 'kill 0' INT TERM EXIT

  uv run uvicorn douyin_crawler.main:app --reload --port 8080 &
  if [[ -x "$BUN_BIN" ]]; then
    (cd frontend && "$BUN_BIN" run dev -- --port 5173) &
  else
    (cd frontend && npm run dev -- --port 5173) &
  fi

  echo "--------------------------------------------------------"
  echo "Frontend (Vite Hot-Reload): http://localhost:5173"
  echo "Backend API & Docs:         http://localhost:8080/docs"
  echo "Nhấn Ctrl+C để dừng cả hai."
  echo "--------------------------------------------------------"
  wait
else
  echo "==> 3. Đang build giao diện Frontend (Vite + shadcn/ui)..."
  if [[ -x "$BUN_BIN" ]]; then
    (cd frontend && "$BUN_BIN" install && "$BUN_BIN" run build)
  elif command -v npm >/dev/null 2>&1; then
    (cd frontend && npm install && npm run build)
  fi

  echo "--------------------------------------------------------"
  echo "Dashboard (Vite + shadcn/ui): http://localhost:8080"
  echo "API Health:                   http://localhost:8080/api/health"
  echo "(Mẹo: dùng './run.sh --dev' nếu muốn chạy Vite Hot-Reload ở cổng 5173)"
  echo "Nhấn Ctrl+C để dừng ứng dụng."
  echo "--------------------------------------------------------"
  exec uv run uvicorn douyin_crawler.main:app --reload --port 8080
fi
