# draw-bitch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Реалтайм-игра «рисуй и угадывай» (Skribbl-подобная) с лобби, очередями ходов, чатом-угадайкой и очками по скорости.

**Architecture:** FastAPI-бэкенд держит всё состояние игры в памяти и общается с браузером по WebSocket; чистая игровая логика (`Lobby`, `scoring`, `words`) отделена от транспорта (`ws.py`) и покрыта pytest. Next.js (standalone) фронтенд — клиентская комната с canvas и хуком WebSocket. Инфра копирует flatinfo: образы в GHCR, авто-деплой по cron, nginx с TLS и проксированием `/ws`.

**Tech Stack:** Python 3.13, FastAPI, uvicorn[standard], uv, ruff, mypy, pytest. Next.js 15, React 19, TypeScript. Docker, GitHub Actions, nginx.

## Global Constraints

- Python: `requires-python == 3.13.*`. Пакетный менеджер — **только uv**.
- Бэкенд-тулинг и пороги — как в flatinfo: ruff (line-length 100, select E,F,I,UP,B,C4), mypy, pytest. Coverage по игровой логике, `main.py`/`ws.py`/`logging_setup.py` исключены из coverage.
- Frontend: Next.js `output: "standalone"`, React 19, TS strict. CI = typecheck + build.
- Комментарии и UI-тексты — **на русском**. Идентификаторы — на английском.
- Состояние игры — **в памяти**, без БД и без Redis.
- Имена образов GHCR: `drawbitch-backend`, `drawbitch-frontend`.
- Связь браузер↔бэкенд: базовый URL из `NEXT_PUBLIC_BACKEND_URL` (пусто = тот же origin).

---

## Структура файлов

```
backend/
  pyproject.toml, uv.lock, Dockerfile, .dockerignore, .env.example, README.md
  app/
    __init__.py
    config.py            # pydantic-settings
    logging_setup.py     # loguru (как flatinfo)
    main.py              # FastAPI + CORS + роутеры + WS
    api.py               # REST: /api/health, POST /api/lobby, GET /api/lobby/{id}
    ws.py                # WebSocket /ws/{lobby_id}: соединения, таймер, рассылка
    schemas.py           # Pydantic-модели REST + WS-сообщений
    game/
      __init__.py
      words.py           # список русских слов + pick_words(n)
      scoring.py         # guesser_points(), drawer_points()
      lobby.py           # класс Lobby: чистая машина состояний
      manager.py         # LobbyManager: словарь лобби
  tests/
    conftest.py
    test_words.py, test_scoring.py, test_lobby.py, test_manager.py, test_api.py
frontend/
  package.json, package-lock.json, next.config.mjs, tsconfig.json, .npmrc, .dockerignore, Dockerfile
  app/
    layout.tsx, globals.css, page.tsx
    lobby/[id]/
      page.tsx           # клиентская комната
      WaitingRoom.tsx, GameBoard.tsx, Canvas.tsx, Toolbar.tsx, Chat.tsx, Scoreboard.tsx, Timer.tsx
  lib/
    types.ts, api.ts, useGameSocket.ts
docker-compose.yml, docker-compose.prod.yml, Makefile, CLAUDE.md, README.md, .gitignore
.github/workflows/ci.yml
deploy/auto-update.sh, deploy/nginx/draw-bitch.conf
```

---

## Task 1: Бэкенд-скаффолд (uv-проект, config, health)

**Files:** Create `backend/pyproject.toml`, `backend/app/{__init__,config,logging_setup,main,api}.py`, `backend/.env.example`, `backend/.dockerignore`, `backend/tests/{conftest,test_api}.py`.

**Interfaces produced:** `app.config.settings` (pydantic Settings с `cors_origins_list`, `round_seconds_default`, `turn_end_pause`, `game_end_pause`, `guesser_base`, `drawer_base`); FastAPI `app` с `GET /api/health` → `{"status":"ok"}`.

- [ ] Создать `pyproject.toml` по образцу flatinfo (deps: fastapi, uvicorn[standard], pydantic, pydantic-settings, loguru; dev: mypy, pytest, pytest-asyncio, pytest-cov, ruff). Coverage omit: `app/main.py`, `app/ws.py`, `app/logging_setup.py`. `uv sync`.
- [ ] `config.py`, `logging_setup.py`, `main.py`, `api.py` (health). Тест `test_api.py::test_health` через `TestClient`. Прогнать `make check`. Commit.

## Task 2: Словарь русских слов (`words.py`)

**Files:** Create `backend/app/game/{__init__,words.py}`, `backend/tests/test_words.py`.

**Interfaces produced:** `WORDS: list[str]` (≥150 русских существительных), `pick_words(n: int = 3) -> list[str]` — n уникальных случайных слов.

- [ ] Тест: `pick_words(3)` возвращает 3 уникальных слова из `WORDS`; `len(WORDS) >= 150`. Реализовать (большой список можно сгенерировать). Commit.

## Task 3: Подсчёт очков (`scoring.py`)

**Files:** Create `backend/app/game/scoring.py`, `backend/tests/test_scoring.py`.

**Interfaces produced:**
- `guesser_points(time_left: float, duration: float, order: int, base: int) -> int` — больше за скорость; небольшой штраф за порядковый номер угадывания; минимальный порог.
- `drawer_points(num_guessed: int, num_potential: int, base: int) -> int` — пропорционально доле угадавших.

- [ ] Тесты: быстрый угадавший > медленного; 0 времени → минимум; рисующий при всех угадавших > при части; деление на ноль безопасно. Реализовать. Commit.

## Task 4: Машина состояний лобби (`lobby.py`) — ядро

**Files:** Create `backend/app/game/lobby.py`, `backend/tests/test_lobby.py`.

**Interfaces produced:** `Phase` (Enum: WAITING/CHOOSING/DRAWING/TURN_END/GAME_END), `Player` (id, name, score, connected), `Stroke`/сегмент рисунка как dict, класс `Lobby`:
- `add_player(name, player_id=None) -> Player`; первый = host.
- `remove_or_offline(player_id)`; передача host при уходе.
- `start_game(by_player_id, round_seconds, total_turns)` — только host, ≥2 игроков → `CHOOSING`, ставит `word_choices`.
- `choose_word(player_id, word)` — только текущий рисующий → `DRAWING`, `started_at` помечается вызывающим (передаётся время).
- `submit_guess(player_id, text, now) -> GuessResult` (правильно/нет, очки, порядок); скрытие текста для остальных.
- `end_turn(now)` — начисляет рисующему, → `TURN_END`; `advance()` → следующий рисующий или `GAME_END`; `reset_to_waiting()`.
- `snapshot()` — полный `state` для рассылки (фаза, игроки, настройки, очки, host_id, drawer_id, маска слова, штрихи, оставшееся время).
- `word_mask` — подчёркивания по длине.
- Нормализация догадки: lower, strip, ё→е.

- [ ] Тесты (по одному поведению): add_player→host; старт <2 запрещён; выбор слова сменяет фазу; правильная догадка даёт очки и не палит слово; все угадали→ end_turn; advance циклит рисующих и завершает игру после N ходов; уход рисующего; передача host; reset_to_waiting обнуляет ход но не игроков (очки сбрасываются в начале новой игры при старте). Реализовать инкрементально. Держать ≥85% покрытия `lobby.py`. Commit по ходу.

## Task 5: Менеджер лобби (`manager.py`)

**Files:** Create `backend/app/game/manager.py`, `backend/tests/test_manager.py`.

**Interfaces produced:** `LobbyManager` с `create() -> Lobby` (генерит короткий id), `get(id) -> Lobby | None`, `remove(id)`. Глобальный `manager`.

- [ ] Тесты: create даёт уникальные id; get несуществующего → None; remove удаляет. Реализовать. Commit.

## Task 6: Схемы сообщений (`schemas.py`)

**Files:** Create `backend/app/schemas.py`.

**Interfaces produced:** Pydantic-модели: REST `CreateLobbyResponse{lobby_id}`, `LobbyExistsResponse{exists}`. WS входящие — discriminated по `type`: join/start_game/choose_word/draw/clear/chat/update_settings. Хелпер сборки исходящих сообщений (dict) — joined/state/turn_start/word_choices/draw/clear/chat/correct_guess/turn_end/game_end/error.

- [ ] Реализовать модели + парсер входящего сообщения `parse_client_message(raw) -> ClientMessage`. (Тестируется косвенно через ws; покрытие не обязательно.) Commit.

## Task 7: REST лобби (`api.py` дополнение)

**Files:** Modify `backend/app/api.py`, `backend/tests/test_api.py`.

**Interfaces produced:** `POST /api/lobby` → `{lobby_id}`; `GET /api/lobby/{id}` → `{exists}`.

- [ ] Тесты: POST создаёт лобби (id в ответе, get→exists True); GET несуществующего → exists False. Реализовать через `manager`. Commit.

## Task 8: WebSocket-эндпоинт (`ws.py`)

**Files:** Create `backend/app/ws.py`; Modify `backend/app/main.py` (подключить WS-роут).

**Interfaces produced:** `WS /ws/{lobby_id}`. На соединение: ждём `join`, выдаём `joined{player_id}` + рассылаем `state`. Обрабатываем сообщения по фазе, рассылаем события. Таймер хода — `asyncio.create_task`, по истечении/всех-угадали зовёт `end_turn` и рассылает `turn_end`, затем планирует `advance`. Хранение соединений `lobby_id -> {player_id: WebSocket}`. Реконнект: повторный `join` с тем же `player_id` помечает connected и шлёт свежий `state`. Дисконнект: offline; если был рисующим в DRAWING/CHOOSING — досрочно завершить ход.

- [ ] Реализовать. Проверка вручную позже через фронт. Лёгкий тест связности через `TestClient` websocket (join→joined). Прогнать `make check`. Commit.

## Task 9: Бэкенд Dockerfile

**Files:** Create `backend/Dockerfile`, `backend/README.md`.

- [ ] Скопировать Dockerfile flatinfo (python:3.13-slim + uv). Commit.

## Task 10: Фронтенд-скаффолд

**Files:** Create `frontend/{package.json,next.config.mjs,tsconfig.json,.npmrc,.dockerignore}`, `frontend/app/{layout.tsx,globals.css}`, `frontend/lib/types.ts`.

**Interfaces produced:** Next 15 standalone, React 19, TS strict; `lib/types.ts` — типы WS-сообщений и состояния (зеркало `schemas.py`).

- [ ] `npm install`; базовый layout (русская локаль, шрифт), globals.css (тёмная минималистичная тема). `npm run typecheck`. Commit.

## Task 11: API-клиент и WS-хук

**Files:** Create `frontend/lib/api.ts`, `frontend/lib/useGameSocket.ts`.

**Interfaces produced:**
- `createLobby(): Promise<string>`, `lobbyExists(id): Promise<boolean>` — REST к `NEXT_PUBLIC_BACKEND_URL`.
- `useGameSocket(lobbyId, name)` → `{state, send, connected}`; реконнект с backoff; player_id из localStorage по ключу `drawbitch:pid:<lobby>`; диспетч входящих в реактивное состояние (накопление штрихов, чат, очки, фаза).

- [ ] Реализовать. typecheck. Commit.

## Task 12: Главная страница (создать/войти)

**Files:** Create `frontend/app/page.tsx`.

- [ ] Форма: секунд на ход (по умолч. 80), число ходов (по умолч. = ходов; напр. 6) — но настройки правит хост в комнате, на главной только «Создать лобби» и поле «вставить ссылку». Кнопка «Создать» → `createLobby()` → `router.push('/lobby/'+id)`. typecheck. Commit.

## Task 13: Комната — каркас и зал ожидания

**Files:** Create `frontend/app/lobby/[id]/page.tsx`, `frontend/app/lobby/[id]/WaitingRoom.tsx`.

- [ ] `page.tsx` — `"use client"`: если нет имени — экран ввода имени; иначе `useGameSocket`. По фазе рендер `WaitingRoom` или `GameBoard`. `WaitingRoom`: список игроков (хост помечен), настройки (секунд/ходов — редактирует только хост, шлёт `update_settings`), ссылка-приглашение + «копировать», кнопка «Старт» у хоста (disabled при <2). typecheck. Commit.

## Task 14: Игровое поле — Canvas, Toolbar

**Files:** Create `frontend/app/lobby/[id]/{GameBoard,Canvas,Toolbar}.tsx`.

**Interfaces produced:** `Canvas` props: `strokes`, `canDraw`, `onSegment`, `onClear`, `color`, `size`. `Toolbar` props: цвет/размер/ластик/очистка.

- [ ] `Canvas`: HTML5 canvas, pointer-события у рисующего → `onSegment({x0,y0,x1,y1,color,size})` (координаты нормализованы 0..1); применяет входящие штрихи из props; ластик = цвет фона. `Toolbar`: 8 цветов, 3 размера, ластик, очистка. `GameBoard`: раскладка (canvas + правая колонка). typecheck. Commit.

## Task 15: Игровое поле — Chat, Scoreboard, Timer, выбор слова

**Files:** Create `frontend/app/lobby/[id]/{Chat,Scoreboard,Timer}.tsx`; Modify `GameBoard.tsx`.

- [ ] `Chat`: лента сообщений (системные «угадал!» выделены) + поле ввода (скрыто/disabled для рисующего и уже угадавших; шлёт `chat`). `Scoreboard`: игроки по очкам, маркер рисующего/онлайн. `Timer`: обратный отсчёт из `state.time_left`. Экран выбора слова (3 кнопки) для рисующего в CHOOSING; маска слова в DRAWING; экран `turn_end` со словом; экран `game_end` с таблицей и (у хоста) «Играть снова». typecheck + `npm run build`. Commit.

## Task 16: Фронтенд Dockerfile

**Files:** Create `frontend/Dockerfile`.

- [ ] Скопировать multistage Dockerfile flatinfo (node:22-slim, standalone). Commit.

## Task 17: Compose-файлы

**Files:** Create `docker-compose.yml`, `docker-compose.prod.yml`.

- [ ] Как flatinfo, но **без redis**. `backend` (loopback :8000, CORS_ORIGINS), `frontend` (loopback :3000, `NEXT_PUBLIC_BACKEND_URL`). prod тянет `ghcr.io/<owner>/drawbitch-{backend,frontend}:latest`. Commit.

## Task 18: CI/CD

**Files:** Create `.github/workflows/ci.yml`.

- [ ] Как flatinfo: job backend (ruff+mypy+pytest), job frontend (typecheck+build), job build-push (master, матрица → `drawbitch-backend`/`drawbitch-frontend` в GHCR, кэш gha). Commit.

## Task 19: Деплой (cron + nginx)

**Files:** Create `deploy/auto-update.sh`, `deploy/nginx/draw-bitch.conf`.

- [ ] `auto-update.sh` — копия flatinfo. nginx: `location /` → :3000; `location /api/` и `location /ws` → :8000 с заголовками `Upgrade`/`Connection` для WebSocket; TLS-блок как flatinfo (домен-плейсхолдер). Commit.

## Task 20: Корневые файлы (Makefile, CLAUDE.md, README, .gitignore)

**Files:** Create `Makefile`, `CLAUDE.md`, `README.md`, `.gitignore`.

- [ ] `Makefile` (check/lint/types/test/back/front/dev) как flatinfo. `CLAUDE.md` — описание архитектуры игры. `README.md` — запуск локально и деплой. `.gitignore` (как flatinfo + node/python). Финальный прогон `make check` и `npm run build`. Commit.

## Self-Review

- Покрытие спеки: слова(T2)/очки(T3)/лобби(T4)/менеджер(T5)/REST(T6,7)/WS+таймер+реконнект+дисконнект(T8)/фронт-фазы(T12-15)/инфра(T9,16-19)/доки(T20) — все разделы спеки покрыты.
- Плейсхолдеров нет.
- Согласованность типов: `snapshot()`→`state`, поля совпадают между `schemas.py`, `lib/types.ts` и компонентами.
