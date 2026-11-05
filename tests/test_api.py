from datetime import datetime

from fastapi.testclient import TestClient

from main import app, connect


def test_index_returns_greeting(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_is_exposed(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json()["version"]


def test_messages_empty_by_default(client):
    assert client.get("/messages").json() == []


def test_add_and_list_message(client):
    response = client.post("/messages", json={"author": "Аня", "text": "Привет!"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    messages = client.get("/messages").json()
    assert len(messages) == 1
    assert messages[0]["author"] == "Аня"
    assert messages[0]["text"] == "Привет!"


def test_messages_newest_first(client):
    client.post("/messages", json={"author": "first", "text": "1"})
    client.post("/messages", json={"author": "second", "text": "2"})

    authors = [m["author"] for m in client.get("/messages").json()]
    assert authors == ["second", "first"]


def test_invalid_message_is_rejected(client):
    response = client.post("/messages", json={"author": "без текста"})
    assert response.status_code == 422


def test_message_has_created_at(client):
    client.post("/messages", json={"author": "Аня", "text": "Привет!"})

    message = client.get("/messages").json()[0]
    assert datetime.fromisoformat(message["created_at"]).tzinfo is not None


def test_migration_from_v1_0_schema_keeps_data():
    """База от v1.0.0 (без created_at) мигрирует на старте, старые записи на месте."""
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS messages")
        conn.execute("CREATE TABLE messages (id SERIAL PRIMARY KEY, author TEXT, text TEXT)")
        conn.execute("INSERT INTO messages (author, text) VALUES ('old', 'из v1.0.0')")

    with TestClient(app) as client:
        messages = client.get("/messages").json()

    assert [(m["author"], m["text"]) for m in messages] == [("old", "из v1.0.0")]
    assert messages[0]["created_at"]


def test_v1_0_queries_still_work_after_migration(client):
    """Обратная совместимость: SQL версии 1.0.0 работает на новой схеме — откат безопасен."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (author, text) VALUES (%s, %s)", ("v1.0.0", "после отката")
        )
        rows = conn.execute("SELECT author, text FROM messages ORDER BY id DESC").fetchall()

    assert rows == [("v1.0.0", "после отката")]
