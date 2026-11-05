#!/usr/bin/env bash
# Выкат и откат гостевой книги из готовых образов ghcr.io.
#
#   scripts/deploy.sh 1.1.0     # выкатить релиз v1.1.0 (можно и с префиксом v)
#   scripts/deploy.sh rollback  # вернуться на предыдущий выкаченный релиз
#   scripts/deploy.sh status    # что сейчас запущено и история выкатов
#
# История выкатов пишется в .deploy-history (по строке на релиз, в .gitignore).
# Данные PostgreSQL лежат в volume pgdata и при выкате/откате не трогаются.
set -euo pipefail

cd "$(dirname "$0")/.."
HISTORY=.deploy-history

[[ -f .env ]] || { echo "Нет .env: cp .env.example .env и задайте POSTGRES_PASSWORD" >&2; exit 1; }

running_version() {
  docker compose exec -T app python -c \
    "import json, urllib.request; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/version'))['version'])"
}

cmd=${1:?"usage: $0 <X.Y.Z>|rollback|status"}
rollback=false

case "$cmd" in
  status)
    echo "Запущено: $(running_version 2>/dev/null || echo 'ничего')"
    echo "История выкатов (последний — внизу):"
    cat "$HISTORY" 2>/dev/null || echo "  пусто"
    exit 0
    ;;
  rollback)
    if [[ ! -f $HISTORY || $(wc -l < "$HISTORY") -lt 2 ]]; then
      echo "Откатываться некуда: в $HISTORY меньше двух выкатов" >&2
      exit 1
    fi
    target=$(tail -n 2 "$HISTORY" | head -n 1)
    rollback=true
    echo "Откат: $(tail -n 1 "$HISTORY") -> $target"
    ;;
  *)
    target=${cmd#v}
    ;;
esac

if [[ ! $target =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Версия должна быть в формате X.Y.Z, получено: $target" >&2
  exit 1
fi

export APP_VERSION=$target

echo "==> pull ghcr.io образа $APP_VERSION"
docker compose pull app

echo "==> запуск (ждём healthcheck app и db)"
docker compose up -d --no-build --wait

actual=$(running_version)
if [[ $actual != "$target" ]]; then
  echo "Ожидали версию $target, а отвечает $actual" >&2
  exit 1
fi

if $rollback; then
  sed -i '$d' "$HISTORY"   # убираем откаченный релиз из истории
else
  echo "$target" >> "$HISTORY"
fi

echo "==> OK: работает версия $actual"
