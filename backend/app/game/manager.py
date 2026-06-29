"""Реестр активных лобби в памяти процесса."""

from __future__ import annotations

import secrets

from app.game.lobby import Lobby

_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # без похожих символов (0/o, 1/l/i)


class LobbyManager:
    def __init__(self) -> None:
        self._lobbies: dict[str, Lobby] = {}

    def _new_id(self) -> str:
        while True:
            lobby_id = "".join(secrets.choice(_ALPHABET) for _ in range(6))
            if lobby_id not in self._lobbies:
                return lobby_id

    def create(self) -> Lobby:
        lobby_id = self._new_id()
        lobby = Lobby(id=lobby_id)
        self._lobbies[lobby_id] = lobby
        return lobby

    def get(self, lobby_id: str) -> Lobby | None:
        return self._lobbies.get(lobby_id)

    def remove(self, lobby_id: str) -> None:
        self._lobbies.pop(lobby_id, None)


manager = LobbyManager()
