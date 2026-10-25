# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim AS frontend-build
ARG PNPM_VERSION=11.23.0
WORKDIR /build/frontend
RUN npm install --global pnpm@${PNPM_VERSION}
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/index.html frontend/vite.config.js frontend/svelte.config.js frontend/jsconfig.json ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN pnpm build

FROM python:3.12-slim-bookworm AS backend-build
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/app ./app
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/backend/.venv/bin:$PATH" \
    DATABASE_URL="sqlite:////data/finance_bro.db" \
    FRONTEND_DIST="/app/frontend/dist"
WORKDIR /app/backend
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app \
    && mkdir /data \
    && chown app:app /data
COPY --from=backend-build /app/backend/.venv ./.venv
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY --from=frontend-build /build/frontend/dist /app/frontend/dist
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).close()"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
