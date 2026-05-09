# syntax=docker/dockerfile:1.7

# --- Stage 1: build frontend assets (Node) ---
FROM node:26-slim AS assets

WORKDIR /src

RUN corepack enable && corepack prepare pnpm@11.0.9 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY web/ ./web/
COPY src/postpit/templates/ ./src/postpit/templates/

RUN pnpm run typecheck && pnpm run assets:build

# --- Stage 2: build python wheel (uv) ---
# Pin uv via versioned image; copy the binary into a standard Python base.
FROM python:3.14-slim-bookworm AS pybuild

COPY --from=ghcr.io/astral-sh/uv:0.11.12 /uv /usr/local/bin/uv

WORKDIR /src

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
COPY --from=assets /src/src/postpit/static/ ./src/postpit/static/

RUN uv build --no-sources --wheel

# --- Stage 3: runtime ---
FROM python:3.14-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/socialpyre/postpit"
LABEL org.opencontainers.image.description="Local mock server for social media platform APIs"
LABEL org.opencontainers.image.licenses="MIT"

RUN useradd -r -u 10001 -m -d /home/postpit -s /usr/sbin/nologin postpit \
 && mkdir -p /data && chown postpit:postpit /data

WORKDIR /app

COPY --from=pybuild /src/dist/*.whl /tmp/

RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

ENV POSTPIT_HOST=0.0.0.0 \
    POSTPIT_PORT=5176 \
    POSTPIT_DATABASE_URL=/data/postpit.db

VOLUME ["/data"]

EXPOSE 5176

USER postpit

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"POSTPIT_PORT\",\"5176\")}/_health',timeout=2).status==200 else 1)"

CMD ["python", "-m", "postpit"]
