from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from pydantic import BaseModel

from config import settings


def connect():
    return psycopg.connect(settings.database_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, author TEXT, text TEXT)"
        )
        # v1.1.0 — expand-миграция: только добавляем колонку с DEFAULT.
        # v1.0.0 вставляет (author, text) и читает (author, text) — новую колонку она не видит,
        # поэтому откат кода на v1.0.0 не требует отката базы.
        conn.execute(
            "ALTER TABLE messages "
            "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        )
    yield


app = FastAPI(lifespan=lifespan)


class Message(BaseModel):
    author: str
    text: str


@app.get("/")
def index():
    return {"message": settings.greeting}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": settings.app_version}


@app.get("/messages")
def list_messages():
    with connect() as conn:
        rows = conn.execute(
            "SELECT author, text, created_at FROM messages ORDER BY id DESC"
        ).fetchall()
    return [
        {"author": author, "text": text, "created_at": created_at.isoformat()}
        for author, text, created_at in rows
    ]


@app.post("/messages")
def add_message(message: Message):
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (author, text) VALUES (%s, %s)",
            (message.author, message.text),
        )
    return {"ok": True}
