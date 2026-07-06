#!/usr/bin/env bash
# frontend と backend を同時に起動する開発用スクリプト
# 使い方: ./dev.sh   (Ctrl+C で両方停止)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  trap - EXIT INT TERM   # 多重実行を防ぐ
  echo ""
  echo "[dev] 停止中..."
  # プロセスグループごと終了させる
  kill 0 2>/dev/null || true
}
trap cleanup INT TERM

echo "[dev] backend  -> http://localhost:8000 (docs: /docs)"
(
  cd "$ROOT/backend"
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --port 8000
) &

echo "[dev] frontend -> http://localhost:5173"
(
  cd "$ROOT/frontend"
  exec pnpm dev
) &

wait
