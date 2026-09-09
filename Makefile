.PHONY: dev backend frontend install test deps-check

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

# requirements.txt のピン留めが「素の環境から」解決できるかを確認する。
# 既存の venv に後から pip install すると依存が黙って持ち上げられ、
# venv の実態と requirements.txt がズレる。ローカルは動くのに Docker ビルドだけ
# 落ちる、という事故がこれで起きたので、requirements.txt を触ったら実行する。
deps-check:
	@rm -rf /tmp/qw-deps-check
	@python3 -m venv /tmp/qw-deps-check
	@/tmp/qw-deps-check/bin/pip install --quiet --upgrade pip
	@/tmp/qw-deps-check/bin/pip install --dry-run -r backend/requirements.txt > /dev/null \
		&& echo "OK: requirements.txt はクリーン環境で解決できます" \
		|| (echo "FAIL: 依存が衝突しています" && /tmp/qw-deps-check/bin/pip install --dry-run -r backend/requirements.txt 2>&1 | tail -20 && exit 1)
	@cd backend && . .venv/bin/activate && pip check
