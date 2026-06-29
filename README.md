# draw-bitch

Минималистичная игра «рисуй и угадывай» для компании друзей. Хост создаёт лобби,
задаёт секунды на ход и число ходов, кидает ссылку. Игроки по очереди рисуют
загаданное слово, остальные угадывают в чате — кто быстрее, тот больше очков.

- **Бэкенд:** Python 3.13, FastAPI, WebSocket, uv. Состояние игры — в памяти.
- **Фронтенд:** Next.js 15 (standalone), React 19, TypeScript, HTML5 canvas.

## Локальный запуск

Нужны `uv` и `node 22+`.

```bash
# 1) бэкенд (http://localhost:8000)
cd backend && uv sync && uv run uvicorn app.main:app --reload

# 2) фронтенд (http://localhost:3000) — в другом терминале
cd frontend && npm install && npm run dev
```

Открой http://localhost:3000, создай лобби, открой ссылку во второй вкладке/устройстве,
введи имена, нажми «Старт». Для игры нужно ≥2 игроков.

Либо весь стек в Docker:

```bash
make dev        # docker compose up --build
```

## Проверки

```bash
make check                       # бэкенд: ruff + mypy + pytest (покрытие ≥85%)
cd frontend && npm run typecheck && npm run build
```

## Деплой и CI/CD

`git push` в `master` запускает GitHub Actions: прогоняет тесты, собирает образы
`drawbitch-backend` и `drawbitch-frontend` и пушит в GHCR.

На сервере (один раз):

1. Положить `docker-compose.prod.yml` и `deploy/` (например, `git clone`).
2. Прописать свой домен вместо `drawbitch.duckdns.org` в `docker-compose.prod.yml`
   (CORS) и `deploy/nginx/draw-bitch.conf`. Владельца образов (`troyan-dy`) в
   `docker-compose.prod.yml` — на свой GitHub-аккаунт.
3. Подключить `deploy/nginx/draw-bitch.conf` к общему nginx, выпустить TLS-сертификат
   (Let's Encrypt webroot → `/var/www/certbot`).
4. Добавить cron на `deploy/auto-update.sh` (раз в несколько минут): тянет свежие
   образы из GHCR и пересоздаёт контейнеры при изменении.

```bash
# первый старт на сервере
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### HTTPS (Let's Encrypt, webroot)

```bash
# первичный выпуск (nginx уже отдаёт /.well-known/acme-challenge/ из /var/www/certbot)
certbot certonly --webroot -w /var/www/certbot -d drawbitch.duckdns.org
# продление обычно ставится в cron самим certbot; конфиг nginx им не редактируется
```

## Особенности

- Состояние игры эфемерно (в памяти бэкенда): перезапуск/деплой обрывает активные игры —
  для вечеринок это приемлемо, БД не нужна.
- WebSocket идёт через тот же домен: nginx роутит `/ws` и `/api` на бэкенд, остальное —
  на фронтенд. Бэкенд наружу закрыт (только loopback).
