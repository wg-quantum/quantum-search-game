# syntax=docker/dockerfile:1
#
# Single-container deployment: FastAPI serves the API *and* the built frontend,
# so the browser talks to one origin and there is no CORS hop in production.
# Port 7860 is what Hugging Face Spaces routes to; override with --port elsewhere.

# ---- stage 1: build the frontend ----
FROM node:24-slim AS web
WORKDIR /web
RUN npm install -g pnpm@10.27.0
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ---- stage 2: python runtime ----
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1: qiskit-aer's manylinux wheels link against OpenMP at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Layout matters: dictionary.py resolves data/ from the package's grandparent,
# and config.py looks for the frontend build at app/static.
COPY backend/app ./app
COPY backend/data ./data
COPY --from=web /web/dist ./app/static

# Spaces runs containers as uid 1000; matching it keeps the image portable.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

# PORT is what most container hosts inject (Render, Code Engine, Cloud Run);
# 7860 is the default because that is the port Hugging Face Spaces routes to.
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
