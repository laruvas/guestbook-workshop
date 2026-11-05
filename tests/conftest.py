"""Тесты ходят в настоящий PostgreSQL.

Локально: поднимите базу (`docker compose up -d db` с пробросом порта или свой Postgres)
и задайте POSTGRES_* в .env. В CI база поднимается как service-контейнер.
"""

import pytest
from fastapi.testclient import TestClient

from main import app, connect


@pytest.fixture
def client():
    # `with` запускает lifespan — он создаёт/мигрирует таблицу, как в проде.
    with TestClient(app) as test_client:
        with connect() as conn:
            conn.execute("TRUNCATE messages RESTART IDENTITY")
        yield test_client
