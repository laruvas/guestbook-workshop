# 📒 Guestbook

[![CI/CD](https://github.com/laruvas/guestbook-workshop/actions/workflows/ci.yml/badge.svg)](https://github.com/laruvas/guestbook-workshop/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/tag/laruvas/guestbook-workshop?label=release&sort=semver)](CHANGELOG.md)

Гостевая книга на FastAPI + PostgreSQL. Само приложение маленькое, главное в репозитории — путь
кода до прода: зафиксированные зависимости, контейнер, CI/CD, релизы по тегам, проверенный откат
и инструкции на случай аварии.

- 🚨 Что-то сломалось → [RUNBOOK.md](RUNBOOK.md)
- 📦 Что изменилось в релизах → [CHANGELOG.md](CHANGELOG.md)
- 🐳 Образы → [ghcr.io/laruvas/guestbook-workshop](https://github.com/laruvas/guestbook-workshop/pkgs/container/guestbook-workshop)

## API

| Метод | Путь | Что делает |
|---|---|---|
| `GET` | `/` | приветствие |
| `GET` | `/health` | сервис жив |
| `GET` | `/version` | какой релиз запущен |
| `GET` | `/messages` | сообщения, новые сверху |
| `POST` | `/messages` | добавить сообщение: `{"author": "...", "text": "..."}` |

## Быстрый старт

Нужны Docker с Compose v2.

```bash
cp .env.example .env          # задайте свой POSTGRES_PASSWORD
docker compose up -d --build  # приложение + PostgreSQL одной командой
curl localhost:8000/health
```

Swagger — http://localhost:8000/docs. Наружу проброшен только порт приложения,
база доступна контейнеру `app` по имени сервиса `db`. Данные хранятся в volume `pgdata`
и переживают `docker compose down` / `up` (их удаляет только `down -v`).

## Конфигурация

Все настройки собраны в [`config.py`](config.py) (pydantic-settings) и читаются из
переменных окружения или `.env`. В коде больше нигде нет `os.environ`, секретов в репозитории нет.

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `POSTGRES_PASSWORD` | — (обязательна) | пароль базы, только в `.env` |
| `POSTGRES_USER` / `POSTGRES_DB` | `guestbook` | пользователь и база |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `localhost` / `5432` | в compose хост переопределён на `db` |
| `APP_PORT` | `8000` | порт на хосте |
| `APP_VERSION` | `dev` | какой образ из ghcr.io запускать; в образ вшивается при сборке |

## Разработка

```bash
uv sync                      # Python 3.13 и зависимости ровно по uv.lock
uv run ruff check . && uv run ruff format --check .
uv run pytest                # нужен PostgreSQL, см. ниже
uv run uvicorn main:app --reload
```

Тесты ходят в настоящую базу. Самый простой способ получить её локально:

```bash
docker run --rm -d --name pg-test -p 5432:5432 \
  -e POSTGRES_USER=guestbook -e POSTGRES_DB=guestbook -e POSTGRES_PASSWORD=test postgres:16-alpine
POSTGRES_PASSWORD=test uv run pytest
```

## CI/CD

Один workflow, [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

```
push / pull_request ──► check: ruff + pytest (на PostgreSQL)
                          │ зелёный, push в main или тег vX.Y.Z
                          ▼
                        publish: образ в ghcr.io
                          │ main  → :latest, :sha-xxxxxxx
                          │ тег   → :X.Y.Z, :X.Y
                          ▼ только для тега
                        release-drill: выкат нового релиза поверх предыдущего
                                       и откат обратно, данные должны выжить
```

На тег `publish` дополнительно проверяет, что коммит есть в `main`, а версия совпадает
с `pyproject.toml` и разделом в `CHANGELOG.md`.

## Как выпустить релиз

1. Внести изменения в `main` (через ветку и merge), дождаться зелёного CI.
2. Поднять версию в `pyproject.toml`, перенести пункты из `[Unreleased]` в новый раздел `CHANGELOG.md`.
3. Закоммитить, поставить тег и запушить:

   ```bash
   git commit -am "release: v1.2.0"
   git tag -a v1.2.0 -m "v1.2.0"
   git push origin main v1.2.0
   ```

4. В Actions пройдут `check` → `publish` → `release-drill`, в Packages появится `:1.2.0`.

Номер версии — по SemVer: исправление → patch, новая обратно совместимая возможность → minor,
несовместимое изменение API → major.

## Выкат и откат

На сервере лежит этот репозиторий (нужны `compose.yaml`, `scripts/` и `.env`):

```bash
scripts/deploy.sh 1.1.0     # выкатить релиз: pull образа, перезапуск, ждём healthcheck, сверяем /version
scripts/deploy.sh rollback  # вернуться на предыдущий выкаченный релиз
scripts/deploy.sh status    # что запущено и история выкатов
```

Если `/version` после выката не совпадает с ожидаемой версией, скрипт завершится с ошибкой.
Подробные сценарии разобраны в [RUNBOOK.md](RUNBOOK.md).

## Инженерные решения

**Стратегия выката — recreate по неизменяемому тегу.** Сервис работает в одном экземпляре
на одном хосте под Compose. Blue-green или canary потребовали бы балансировщик и второй экземпляр,
а для гостевой книги несколько секунд простоя на рестарте допустимы. Взамен откат устроен просто
и всегда одинаково: каждый релиз — неизменяемый образ `:X.Y.Z`, откат — это выкат предыдущего тега
той же командой. Откат репетируется в CI на каждом релизе (`release-drill`), поэтому он проверен
до того, как понадобится в аварии.

**Схема БД меняется только обратно совместимо (expand → contract).** Миграции выполняет
приложение при старте и только *расширяют* схему: новые колонки добавляются с `DEFAULT`, ничего
не удаляется и не переименовывается в том же релизе. Поэтому предыдущая версия продолжает
работать на новой схеме, и откат кода не требует отката базы.
Удаление старого (contract) делается отдельным релизом, когда к прошлой версии точно не вернёмся.

Пример — релиз 1.1.0 добавил время создания сообщения:

```sql
ALTER TABLE messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
```

- Версия 1.0.0 делает `INSERT (author, text)` — колонку заполнит `DEFAULT`, `NOT NULL` не нарушается.
- Версия 1.0.0 делает `SELECT author, text` — лишняя колонка ей не мешает.
- `IF NOT EXISTS` делает миграцию идемпотентной: повторный выкат 1.1.0 после отката ничего не ломает.
- В PostgreSQL 11+ `ADD COLUMN ... DEFAULT` не переписывает таблицу, блокировка короткая.

Это проверяется дважды: тестом `test_v1_0_queries_still_work_after_migration` и учениями
`release-drill`, где 1.1.0 откатывается на 1.0.0 с живыми данными.

## Структура

```
main.py              эндпоинты и миграция схемы при старте
config.py            все настройки (pydantic-settings)
tests/               pytest на настоящем PostgreSQL
Dockerfile           образ: uv sync --locked, затем код, запуск не от root
compose.yaml         app + db, healthcheck, volume
scripts/deploy.sh    выкат / откат / статус
.github/workflows/   CI/CD
```
