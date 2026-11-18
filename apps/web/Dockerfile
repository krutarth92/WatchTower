# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS build

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"

WORKDIR /app

RUN corepack enable \
    && corepack prepare pnpm@12.14.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @watchtower/web build

FROM node:24-bookworm-slim AS runtime

ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000

WORKDIR /app

RUN groupadd --system --gid 10001 watchtower \
    && useradd --system --uid 10001 --gid watchtower --home-dir /app watchtower

COPY --from=build --chown=watchtower:watchtower /app/apps/web/build ./build

USER watchtower
EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=4 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/search').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]

CMD ["node", "build"]
