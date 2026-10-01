# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.12.19 AS uv
FROM python:3.14.7-slim-bookworm AS runtime

COPY --from=uv /uv /uvx /bin/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app

RUN groupadd --system --gid 10001 watchtower \
    && useradd --system --uid 10001 --gid watchtower --home-dir /app watchtower

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY apps/api/src ./apps/api/src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
RUN uv sync --locked --no-dev \
    && mkdir -p /var/lib/watchtower/raw \
    && chown -R watchtower:watchtower /var/lib/watchtower \
    && rm -f /bin/uv /bin/uvx

USER watchtower
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=4 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2).read()"]

CMD ["uvicorn", "watchtower.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
