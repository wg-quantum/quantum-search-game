.PHONY: dev backend frontend install test

# frontend と backend を同時に起動 (Ctrl+C で両方停止)
dev:
	@./dev.sh

# backend のみ起動
backend:
	@cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

# frontend のみ起動
frontend:
	@cd frontend && pnpm dev

# 依存関係のインストール
install:
	@cd backend && . .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt
	@cd frontend && pnpm install

# テスト実行 (backend + frontend)
test:
	@cd backend && . .venv/bin/activate && pytest
	@cd frontend && pnpm test
