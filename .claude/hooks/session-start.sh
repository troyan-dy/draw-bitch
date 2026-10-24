#!/bin/bash
# SessionStart-хук для облачных сессий Claude Code: ставит зависимости бэкенда (uv)
# и фронтенда (npm), чтобы сразу работали make check и npm run typecheck/build.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

# Бэкенд: uv сам скачает нужный Python (requires-python) и поставит dev-группу.
if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --quiet --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi
(cd backend && uv sync --frozen)
# Проверка, что линтеры из dev-группы на месте (ruff, flake8 + WPS).
(cd backend && uv run ruff --version && uv run flake8 --version) >/dev/null

# Фронтенд: npm install (а не ci) — переиспользует закэшированный node_modules.
(cd frontend && npm install --no-audit --no-fund)
