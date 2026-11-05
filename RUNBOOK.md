# 🚨 RUNBOOK — гостевая книга

Аварийная инструкция: что проверить и что делать. Все команды выполняются на сервере
из каталога с репозиторием (там, где лежат `compose.yaml` и `.env`).

## Паспорт сервиса

| | |
|---|---|
| Что это | FastAPI-приложение `app` + PostgreSQL 16 `db`, docker compose, один хост |
| Порт | `APP_PORT` из `.env` (по умолчанию 8000), наружу открыт только `app` |
| Образы | `ghcr.io/laruvas/guestbook-workshop:X.Y.Z` — один неизменяемый образ на релиз |
| Данные | volume `pgdata` (`docker volume ls`, имя `<каталог>_pgdata`) |
| Секреты | только `.env` на сервере, в git его нет |
| Выкат / откат | `scripts/deploy.sh X.Y.Z` / `scripts/deploy.sh rollback` |
| Изменения по версиям | [CHANGELOG.md](CHANGELOG.md) |

## 1. Первичная диагностика (2 минуты)

```bash
scripts/deploy.sh status                   # какая версия запущена, история выкатов
docker compose ps                          # оба контейнера Up и (healthy)?
curl -fsS localhost:8000/health            # {"status":"ok"}
curl -fsS localhost:8000/messages | head   # отвечает ли база
docker compose logs --tail=100 app
docker compose logs --tail=100 db
```

Дальше — по симптому.

## 2. Сломалось после выката → откат

Первое действие при любой проблеме, появившейся после выката: **сначала откатиться, потом разбираться.**

```bash
scripts/deploy.sh rollback
scripts/deploy.sh status       # должна быть предыдущая версия
curl -fsS localhost:8000/messages
```

Базу откатывать не нужно: миграции только расширяют схему (см. README → «Инженерные решения»),
предыдущая версия работает на новой схеме.

Если `.deploy-history` нет или он испорчен, откатитесь на конкретную версию явно — список релизов
в [CHANGELOG.md](CHANGELOG.md) и в Packages на GitHub:

```bash
scripts/deploy.sh 1.0.0
```

После отката: заведите issue, в `CHANGELOG.md` в `[Unreleased]` опишите проблему,
исправление выпускайте новым patch-релизом. Сломанный тег не переставляйте.

## 3. `app` не стартует или в статусе unhealthy

| Что видно в `docker compose logs app` | Причина | Что делать |
|---|---|---|
| `ValidationError ... postgres_password Field required` | нет `POSTGRES_PASSWORD` в `.env` | заполнить `.env` по `.env.example`, `docker compose up -d` |
| `connection refused` / `could not translate host name "db"` | база не поднялась | раздел 4 |
| `password authentication failed` | пароль в `.env` не совпадает с паролем в базе | раздел 6 |
| `manifest unknown` при `deploy.sh` | такой версии нет в ghcr.io | проверить тег в Packages, версию писать без `v` или с ним — оба варианта работают |
| `denied` / `unauthorized` при pull | нет доступа к ghcr.io | `docker login ghcr.io -u <github-логин>` с токеном `read:packages` |

Перезапуск без смены версии:

```bash
docker compose restart app
```

## 4. `db` не стартует или unhealthy

```bash
docker compose logs --tail=100 db
df -h                                   # кончилось место?
docker system df                        # сколько занимают образы и volume
```

- **Нет места:** `docker image prune -a` (удалит неиспользуемые образы; volume с данными не трогает), затем `docker compose up -d`.
- **Данные повреждены:** восстановиться из бэкапа (раздел 5).
- ⚠️ **Никогда** не запускайте `docker compose down -v` и `docker volume rm` на проде — это удаляет все сообщения.

## 5. Бэкап и восстановление

Бэкап (делайте перед каждым выкатом с изменением схемы):

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup-$(date +%F-%H%M).sql
```

Восстановление в работающую базу:

```bash
docker compose stop app
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP TABLE IF EXISTS messages"'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backup-YYYY-MM-DD-HHMM.sql
docker compose start app
```

## 6. Утечка или смена пароля базы

`POSTGRES_PASSWORD` в compose применяется только при **первой** инициализации volume.
Поэтому для смены пароля мало поправить `.env` — его надо поменять и в самой базе:

```bash
openssl rand -hex 16          # сгенерировать новый пароль
docker compose exec db psql -U guestbook -d guestbook -c "ALTER USER guestbook PASSWORD '<новый-пароль>'"
# вписать <новый-пароль> в POSTGRES_PASSWORD в .env
docker compose up -d          # пересоздаст app с новым паролем
curl -fsS localhost:8000/messages
```

Если пароль попал в git: смена пароля обязательна, удаление коммита не помогает — его уже могли скачать.

## 7. Плановый выкат

1. Убедиться, что для тега в Actions зелёные `check`, `publish` и `release-drill`.
2. Прочитать раздел версии в [CHANGELOG.md](CHANGELOG.md). Если меняется схема, сделать бэкап (раздел 5).
3. Выкатить и проверить:

   ```bash
   scripts/deploy.sh X.Y.Z
   curl -fsS localhost:8000/messages | head
   ```

4. Если что-то не так — раздел 2.
