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
