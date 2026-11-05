# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# uv закреплён по версии — сборка воспроизводима
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/

WORKDIR /app

# сначала зависимости (слой кэшируется), потом код
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY . .

# версия релиза вшивается при сборке (CI передаёт её из git-тега), видна в GET /version
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    PATH="/app/.venv/bin:$PATH"

# приложение не работает от root
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
