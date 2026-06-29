#!/usr/bin/env bash
#
# Авто-деплой: тянет свежие образы из GHCR и, ТОЛЬКО если они изменились,
# пересоздаёт контейнеры из docker-compose.prod.yml. Сборки на сервере нет —
# образы собирает GitHub Actions (.github/workflows/ci.yml). Состояние игры
# эфемерно (в памяти бэкенда), пересоздание обрывает активные игры.
#
# Запускается из cron раз в несколько минут. Идемпотентен: образы не менялись —
# тихо выходит. docker-compose.prod.yml кладётся на сервер один раз при установке.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml)
LOG="$SCRIPT_DIR/auto-update.log"
LOCK="$SCRIPT_DIR/.auto-update.lock"

log() { echo "[$(date '+%F %T')] $*" >>"$LOG"; }

# Защита от наложения запусков.
exec 9>"$LOCK"
if ! flock -n 9; then
  log "previous run still in progress, skip"
  exit 0
fi

images="$("${COMPOSE[@]}" config --images)"
before="$(docker image inspect --format '{{.Id}}' $images 2>/dev/null | sort || true)"

"${COMPOSE[@]}" pull --quiet >>"$LOG" 2>&1

after="$(docker image inspect --format '{{.Id}}' $images 2>/dev/null | sort || true)"

if [ "$before" = "$after" ]; then
  exit 0
fi

log "new images pulled, recreating containers..."
"${COMPOSE[@]}" up -d >>"$LOG" 2>&1
log "done"

docker image prune -f >>"$LOG" 2>&1 || true
