# syntax=docker/dockerfile:1
# Chainguard images carry no distribution packages, so the image scan has nothing to report but Python itself (ADR 0006).
FROM cgr.dev/chainguard/python:latest-dev@sha256:9f76d277ca81d3079eb3be24c742de3b6598f032fc9943fed6951ff99e581d02 AS build
USER root
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /usr/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PYTHON=/usr/bin/python
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM cgr.dev/chainguard/python:latest@sha256:e5322b9d32064a645225b8b2419f11127bcf2d8b9927f9514f0acee1e1d25751
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
