.PHONY: check lint types test back front dev

# Все проверки бэкенда одной командой.
check: lint types test

lint:
	cd backend && uv run ruff check .

types:
	cd backend && uv run mypy

test:
	cd backend && uv run pytest -q

# Локальный запуск.
back:
	cd backend && uv run uvicorn app.main:app --reload

front:
	cd frontend && npm run dev

# Полный стек в Docker.
dev:
	docker compose up --build
