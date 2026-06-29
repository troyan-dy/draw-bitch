# draw-bitch — рисуй и угадывай

Реалтайм-игра в духе Skribbl. Хост создаёт лобби, кидает ссылку друзьям. Игроки по
очереди рисуют загаданное слово, остальные угадывают в чате; кто быстрее — тем больше
очков. Бэкенд (FastAPI) держит всё состояние **в памяти** и общается с браузером по
WebSocket; фронтенд (Next.js) — клиентская игровая комната.

## Поток игры

`WAITING` → `CHOOSING` (рисующий выбирает 1 из 3 русских слов) → `DRAWING` (рисует,
идёт таймер, остальные угадывают) → `TURN_END` (показали слово, начислили очки, пауза) →
следующий ход… после N ходов → `GAME_END` (итоговая таблица) → `WAITING`.

«Раунд» из ТЗ = один ход рисования; хост задаёт число ходов и секунды на ход.

## Архитектура

### Бэкенд (`backend/app/`)
- `game/lobby.py` — класс `Lobby`: **чистая** машина состояний без сети и таймеров;
  реальное время приходит аргументом `now`. Здесь вся логика: очерёдность, угадывание,
  очки, снимок состояния (`snapshot`). Покрыт тестами.
- `game/manager.py` — `LobbyManager`: реестр лобби по короткому id.
- `game/scoring.py` — чистые формулы очков (угадавший по скорости, бонус рисующему).
- `game/words.py` — встроенный список русских слов + `pick_words(3)`.
- `ws.py` — WebSocket `/ws/{lobby_id}`: соединения, рассылка, таймер хода (asyncio),
  реконнект по `player_id`, досрочное завершение при уходе рисующего. **Транспорт**,
  логики игры не содержит — дёргает методы `Lobby`.
- `api.py` — REST: `/api/health`, `POST /api/lobby`, `GET /api/lobby/{id}`.
- `schemas.py` — Pydantic-модели входящих WS-сообщений (`parse_client_message`) и REST.
- `config.py` — pydantic-settings (CORS, дефолты/границы игры, размеры очков и пауз).

Состояние **эфемерно**: перезапуск/деплой обрывает активные игры. БД и Redis нет.

### Фронтенд (`frontend/`)
- `lib/types.ts` — типы сообщений и состояния (зеркало `schemas.py`/`snapshot`).
- `lib/api.ts` — REST-вызовы и сборка WS-URL. Базовый адрес — `NEXT_PUBLIC_BACKEND_URL`
  (пусто = тот же origin; в проде nginx роутит `/api` и `/ws` на бэкенд).
- `lib/useGameSocket.ts` — хук WS: соединение, реконнект с backoff, `player_id` в
  localStorage, диспетч входящих сообщений в реактивное состояние (штрихи, чат, очки).
- `app/page.tsx` — главная (создать лобби / войти по ссылке).
- `app/lobby/[id]/page.tsx` — комната: экран имени → подключение → по фазе `WaitingRoom`
  или `GameBoard`.
- `app/lobby/[id]/` — `WaitingRoom`, `GameBoard`, `Canvas` (нормализованные 0..1 штрихи),
  `Toolbar` (8 цветов, 3 размера, ластик, очистка), `Chat`, `Scoreboard`, `Timer`.

## Команды

```bash
# бэкенд
cd backend && uv sync
uv run uvicorn app.main:app --reload      # http://localhost:8000, /docs
make check                                 # ruff + mypy + pytest

# фронтенд
cd frontend && npm install
npm run dev                                # http://localhost:3000
npm run typecheck && npm run build

# весь стек в Docker
make dev                                    # docker compose up --build
```

## Договорённости

- Комментарии и UI-тексты — на русском. Идентификаторы — на английском.
- Логика игры живёт в `Lobby` и покрыта тестами; `ws.py` — только транспорт (исключён
  из coverage). Меняешь правила игры → меняешь `Lobby` + тесты, не `ws.py`.
- Координаты рисунка нормализованы (0..1) — холсты разного размера совпадают.
- Слово не раскрывается угадывающим: `snapshot(for_player=...)` отдаёт `word` только
  рисующему и уже угадавшим; остальным — маска из подчёркиваний.

## Деплой

CI (`.github/workflows/ci.yml`): тесты → сборка образов `drawbitch-backend`/
`drawbitch-frontend` в GHCR (на master). На сервере cron гоняет `deploy/auto-update.sh`:
тянет образы и пересоздаёт контейнеры при изменении. Публичный вход — общий nginx
(`deploy/nginx/draw-bitch.conf`) с TLS; `/ws` и `/api` → бэкенд, `/` → фронтенд.
