# syntax=docker/dockerfile:1
# Chainguard images carry no distribution packages, so the image scan has nothing to report but Python itself (ADR 0006).
FROM cgr.dev/chainguard/python:latest-dev@sha256:3ca53097911a867be4f8190b8bc272d1465e9d95ef32ecc2cd70d841e2baeac3 AS build
USER root
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PYTHON=/usr/bin/python
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# The forecaster has its own image: Prophet, cmdstan and the scientific libraries stay out of api and worker (ADR 0107).
FROM cgr.dev/chainguard/python:latest-dev@sha256:3ca53097911a867be4f8190b8bc272d1465e9d95ef32ecc2cd70d841e2baeac3 AS forecaster-build
USER root
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PYTHON=/usr/bin/python
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --only-group forecaster --no-install-project

FROM cgr.dev/chainguard/python:latest@sha256:3a89a9027f47e44e9f9da201493013249a02fc87fa7269bba80f621d7ade83f8 AS forecaster
ARG REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/ElettroAle/autotrading"       org.opencontainers.image.revision="${REVISION}"
COPY --from=forecaster-build /app/.venv /app/.venv
COPY forecaster /app/forecaster
# cmdstan and matplotlib write only temporary files: the compose mounts /tmp as tmpfs on a read-only filesystem.
ENV PATH="/app/.venv/bin:${PATH}" PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8000
ENTRYPOINT ["/app/.venv/bin/python", "-m", "uvicorn"]
CMD ["forecaster.service:create_application", "--factory", "--host", "0.0.0.0", "--port", "8000"]

# The dashboard has its own image (ADR 0116, ADR 0117): the Vite build, served read only by the small Node server of
# dashboard/server as the non-root user of the image. No secret: the configuration comes from public variables.
FROM cgr.dev/chainguard/node:latest-dev@sha256:7393e94262396c74c4101cb1578f666b1f76884f48082ab59beb5e171271af5c AS dashboard-build
USER root
WORKDIR /app
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY dashboard ./
RUN npx vite build

FROM cgr.dev/chainguard/node:latest@sha256:86d7c621851bf0589807dcb060aea8295987464efd378cefd46e44f1f3b6ce73 AS dashboard
ARG REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/ElettroAle/autotrading"       org.opencontainers.image.revision="${REVISION}"
COPY dashboard/package.json /app/package.json
COPY dashboard/server /app/server
COPY --from=dashboard-build /app/dist /app/dist
ENV DASHBOARD_ROOT=/app/dist DASHBOARD_PORT=8080 NODE_ENV=production
EXPOSE 8080
ENTRYPOINT ["/usr/bin/node"]
CMD ["/app/server/main.ts"]

# The last stage is the default target: the image of api, worker and migrate.
FROM cgr.dev/chainguard/python:latest@sha256:3a89a9027f47e44e9f9da201493013249a02fc87fa7269bba80f621d7ade83f8
ARG REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/ElettroAle/autotrading" \
      org.opencontainers.image.revision="${REVISION}"
COPY --from=build /app/.venv /app/.venv
# The migrate service of the compose runs Alembic from the same image (ADR 0015).
COPY migrations /app/migrations
COPY deploy/logging.json /app/logging.json
ENV PATH="/app/.venv/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
ENTRYPOINT ["/app/.venv/bin/python", "-m", "uvicorn"]
CMD ["autotrading.bootstrap:create_application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--log-config", "/app/logging.json"]
