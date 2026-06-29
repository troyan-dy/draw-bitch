"""WebSocket-транспорт: соединения, рассылка событий, таймер хода.

Игровая логика живёт в `Lobby`; здесь — только сеть и оркестровка по времени.
На каждое лобби держим карту `player_id -> WebSocket`. Реальное время берём из
`time.monotonic()` и передаём в методы лобби.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger

from app.config import settings
from app.game.lobby import Lobby, Phase
from app.game.manager import manager
from app.schemas import (
    ChatMsg,
    ChooseWordMsg,
    DrawMsg,
    JoinMsg,
    StartGameMsg,
    UpdateSettingsMsg,
    msg,
    parse_client_message,
)


class Hub:
    """Соединения и таймеры одного лобби."""

    def __init__(self, lobby: Lobby) -> None:
        self.lobby = lobby
        self.connections: dict[str, WebSocket] = {}
        self._turn_task: asyncio.Task[None] | None = None

    async def send(self, player_id: str, message: dict[str, Any]) -> None:
        ws = self.connections.get(player_id)
        if ws is None:
            return
        try:
            await ws.send_json(message)
        except Exception:  # соединение умерло — уберём при дисконнекте
            pass

    async def broadcast(self, message: dict[str, Any]) -> None:
        for pid in list(self.connections):
            await self.send(pid, message)

    async def broadcast_state(self) -> None:
        """Каждому шлём персонализированный снимок (рисующий/угадавшие видят слово)."""
        now = time.monotonic()
        for pid in list(self.connections):
            await self.send(pid, msg("state", **self.lobby.snapshot(now, for_player=pid)))

    # ---- Таймер хода ------------------------------------------------------

    def cancel_turn_timer(self) -> None:
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        self._turn_task = None

    def start_turn_timer(self) -> None:
        self.cancel_turn_timer()
        self._turn_task = asyncio.create_task(self._run_turn(self.lobby.turn_index))

    async def _run_turn(self, turn_index: int) -> None:
        """Ждём конца таймера и завершаем ход, если он ещё тот же самый."""
        try:
            await asyncio.sleep(self.lobby.round_seconds)
            if self.lobby.phase == Phase.DRAWING and self.lobby.turn_index == turn_index:
                await self.finish_turn()
        except asyncio.CancelledError:
            pass

    async def finish_turn(self) -> None:
        """Завершить ход досрочно/по таймеру, показать слово, запланировать переход."""
        self.cancel_turn_timer()
        word = self.lobby.word
        self.lobby.end_turn()
        scores = {p["id"]: p["score"] for p in self.lobby.snapshot(time.monotonic())["players"]}
        await self.broadcast(msg("turn_end", word=word, scores=scores))
        await self.broadcast_state()
        self._turn_task = asyncio.create_task(self._after_turn_end(self.lobby.turn_index))

    async def _after_turn_end(self, turn_index: int) -> None:
        try:
            await asyncio.sleep(settings.turn_end_pause)
            if self.lobby.turn_index != turn_index or self.lobby.phase != Phase.TURN_END:
                return
            self.lobby.advance()
            if self.lobby.phase == Phase.GAME_END:
                await self.broadcast(msg("game_end"))
                await self.broadcast_state()
                self._turn_task = asyncio.create_task(self._after_game_end())
            else:
                await self.begin_choosing()
        except asyncio.CancelledError:
            pass

    async def _after_game_end(self) -> None:
        try:
            await asyncio.sleep(settings.game_end_pause)
            if self.lobby.phase == Phase.GAME_END:
                self.lobby.phase = Phase.WAITING
                await self.broadcast_state()
        except asyncio.CancelledError:
            pass

    async def begin_choosing(self) -> None:
        """Разослать состояние выбора слова: рисующему — варианты, всем — снимок."""
        await self.broadcast_state()
        if self.lobby.drawer_id:
            await self.send(
                self.lobby.drawer_id, msg("word_choices", words=self.lobby.word_choices)
            )

    async def maybe_finish_on_disconnect(self, player_id: str) -> None:
        """Если ушёл рисующий во время хода — завершаем ход досрочно."""
        if self.lobby.drawer_left_during_turn(player_id):
            await self.finish_turn()


_hubs: dict[str, Hub] = {}


def _hub_for(lobby: Lobby) -> Hub:
    hub = _hubs.get(lobby.id)
    if hub is None:
        hub = Hub(lobby)
        _hubs[lobby.id] = hub
    return hub


def register_ws(app: FastAPI) -> None:
    @app.websocket("/ws/{lobby_id}")
    async def game_ws(ws: WebSocket, lobby_id: str) -> None:
        lobby = manager.get(lobby_id)
        if lobby is None:
            await ws.accept()
            await ws.send_json(msg("error", message="Лобби не существует"))
            await ws.close()
            return

        await ws.accept()
        hub = _hub_for(lobby)
        player_id: str | None = None
        try:
            while True:
                raw = await ws.receive_json()
                message = parse_client_message(raw)
                if message is None:
                    continue
                player_id = await _handle(hub, ws, lobby, player_id, message)
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("ws error in lobby {}: {}", lobby_id, exc)
        finally:
            if player_id and hub.connections.get(player_id) is ws:
                hub.connections.pop(player_id, None)
                lobby.mark_offline(player_id)
                await hub.maybe_finish_on_disconnect(player_id)
                await hub.broadcast_state()
                if lobby.empty:
                    hub.cancel_turn_timer()
                    _hubs.pop(lobby.id, None)
                    manager.remove(lobby.id)


async def _handle(
    hub: Hub,
    ws: WebSocket,
    lobby: Lobby,
    player_id: str | None,
    message: Any,
) -> str | None:
    """Обработать одно сообщение, вернуть актуальный player_id."""
    # До join принимаем только join.
    if player_id is None:
        if not isinstance(message, JoinMsg):
            return None
        player = lobby.add_player(message.name, message.player_id)
        hub.connections[player.id] = ws
        await hub.send(player.id, msg("joined", player_id=player.id))
        await hub.broadcast_state()
        # Реконнект во время выбора слова — вернуть варианты рисующему.
        if lobby.phase == Phase.CHOOSING and lobby.drawer_id == player.id:
            await hub.send(player.id, msg("word_choices", words=lobby.word_choices))
        return player.id

    now = time.monotonic()

    if isinstance(message, JoinMsg):
        return player_id  # уже в игре, повторный join игнорируем

    if isinstance(message, StartGameMsg):
        if lobby.start_game(player_id):
            await hub.begin_choosing()

    elif isinstance(message, UpdateSettingsMsg):
        if lobby.update_settings(player_id, message.round_seconds, message.total_turns):
            await hub.broadcast_state()

    elif isinstance(message, ChooseWordMsg):
        if lobby.choose_word(player_id, message.word, now):
            await hub.broadcast_state()
            hub.start_turn_timer()

    elif isinstance(message, DrawMsg):
        if lobby.add_stroke(player_id, message.segment.model_dump()):
            await hub.broadcast(msg("draw", segment=message.segment.model_dump()))

    elif message_is_clear(message):
        if lobby.clear_canvas(player_id):
            await hub.broadcast(msg("clear"))

    elif isinstance(message, ChatMsg):
        await _handle_chat(hub, lobby, player_id, message, now)

    return player_id


def message_is_clear(message: Any) -> bool:
    return getattr(message, "type", None) == "clear"


async def _handle_chat(
    hub: Hub, lobby: Lobby, player_id: str, message: ChatMsg, now: float
) -> None:
    result = lobby.submit_guess(player_id, message.text, now)
    if result.correct:
        # Слово не палим: всем — факт угадывания, без текста.
        await hub.broadcast(
            msg("correct_guess", player_id=player_id, points=result.points)
        )
        await hub.broadcast_state()
        if result.all_guessed:
            await hub.finish_turn()
    else:
        # Обычное сообщение: рисующему и уже угадавшим не показываем чужие догадки
        # только если игра идёт; в остальных фазах чат общий.
        await _broadcast_chat(hub, lobby, player_id, message.text)


async def _broadcast_chat(hub: Hub, lobby: Lobby, player_id: str, text: str) -> None:
    """Рассылка обычного чат-сообщения.

    Во время DRAWING те, кто уже угадал (и рисующий), переписываются отдельно —
    их сообщения не видят те, кто ещё угадывает, чтобы не подсказать слово.
    """
    payload = msg("chat", player_id=player_id, text=text)
    if lobby.phase != Phase.DRAWING:
        await hub.broadcast(payload)
        return
    sender_knows = player_id == lobby.drawer_id or player_id in lobby.guessed
    for pid in list(hub.connections):
        receiver_knows = pid == lobby.drawer_id or pid in lobby.guessed
        if sender_knows and not receiver_knows:
            continue  # знающий пишет — не показываем ещё не угадавшим
        await hub.send(pid, payload)
