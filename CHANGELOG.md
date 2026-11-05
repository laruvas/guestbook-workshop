# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии — [SemVer](https://semver.org/lang/ru/).
Каждый релиз — git-тег `vX.Y.Z` и образ `ghcr.io/laruvas/guestbook-workshop:X.Y.Z`.

## [Unreleased]

## [1.0.0] - 2026-11-05

Первый релиз, доведённый до прода.

### Added
- Зависимости на uv (`pyproject.toml` + `uv.lock`), Python 3.13 закреплён в `.python-version`.
- Dockerfile (зависимости до кода, uv закреплён, запуск не от root) и `.dockerignore`.
- `compose.yaml`: приложение + PostgreSQL 16, healthcheck, `depends_on: service_healthy`, volume `pgdata`.
- Конфиг на pydantic-settings (`config.py`), секреты только в `.env`, в репозитории `.env.example`.
- `GET /version` — какой релиз сейчас запущен.
- CI: Ruff (lint + format) и pytest на настоящем PostgreSQL на каждый push и pull request.
- CD: публикация образа в ghcr.io после зелёного CI, только из `main` (`latest`, `sha-…`) и тегов (`X.Y.Z`, `X.Y`).
- Учения релиза в CI: выкат нового тега поверх предыдущего и откат обратно.
- `scripts/deploy.sh` — выкат по версии и откат (`rollback`).
- README и RUNBOOK.

### Removed
- `requirements.txt` и зашитый в код пароль базы.

[Unreleased]: https://github.com/laruvas/guestbook-workshop/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/laruvas/guestbook-workshop/releases/tag/v1.0.0
