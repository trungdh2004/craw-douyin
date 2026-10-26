#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

echo "Dashboard: http://localhost:8080"
echo "Nhấn Ctrl+C để dừng ứng dụng."
exec uv run uvicorn douyin_crawler.main:app --reload --port 8080
