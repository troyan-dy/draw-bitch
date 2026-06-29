# draw-bitch backend

FastAPI + WebSocket. Всё состояние игры — в памяти процесса (без БД/Redis).

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000, /docs
uv run ruff check . && uv run mypy && uv run pytest -q
```

- REST: `GET /api/health`, `POST /api/lobby`, `GET /api/lobby/{id}`.
- WebSocket: `/ws/{lobby_id}` — основной игровой канал (см. `app/schemas.py`).
- Логика игры: `app/game/` (`lobby.py`, `manager.py`, `scoring.py`, `words.py`).
