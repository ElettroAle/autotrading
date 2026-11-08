# syntax=docker/dockerfile:1
FROM python:3.12-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-trixie
ARG REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/ElettroAle/autotrading" \
      org.opencontainers.image.revision="${REVISION}"
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1
USER 10001
EXPOSE 8000
CMD ["uvicorn", "autotrading.bootstrap:create_application", "--factory", "--host", "0.0.0.0", "--port", "8000"]
