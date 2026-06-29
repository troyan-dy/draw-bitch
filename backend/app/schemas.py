"""Pydantic-модели REST-ответов и входящих WebSocket-сообщений.

Исходящие WS-сообщения собираются как обычные dict (хелперы внизу) — так проще
рассылать смешанные полезные нагрузки, включая полный снимок состояния лобби.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

# ---- REST -----------------------------------------------------------------

class CreateLobbyResponse(BaseModel):
    lobby_id: str


class LobbyExistsResponse(BaseModel):
    exists: bool


# ---- Входящие WebSocket-сообщения -----------------------------------------

class JoinMsg(BaseModel):
    type: Literal["join"]
    name: str = Field(default="", max_length=24)
    player_id: str | None = None


class StartGameMsg(BaseModel):
    type: Literal["start_game"]


class UpdateSettingsMsg(BaseModel):
    type: Literal["update_settings"]
    round_seconds: int
    total_turns: int


class ChooseWordMsg(BaseModel):
    type: Literal["choose_word"]
    word: str


class Segment(BaseModel):
    # Координаты нормализованы в 0..1 относительно холста.
    x0: float
    y0: float
    x1: float
    y1: float
    color: str = Field(max_length=16)
    size: float


class DrawMsg(BaseModel):
    type: Literal["draw"]
    segment: Segment


class ClearMsg(BaseModel):
    type: Literal["clear"]


class ChatMsg(BaseModel):
    type: Literal["chat"]
    text: str = Field(max_length=200)


ClientMessage = (
    JoinMsg
    | StartGameMsg
    | UpdateSettingsMsg
    | ChooseWordMsg
    | DrawMsg
    | ClearMsg
    | ChatMsg
)

_BY_TYPE: dict[str, type[BaseModel]] = {
    "join": JoinMsg,
    "start_game": StartGameMsg,
    "update_settings": UpdateSettingsMsg,
    "choose_word": ChooseWordMsg,
    "draw": DrawMsg,
    "clear": ClearMsg,
    "chat": ChatMsg,
}


def parse_client_message(raw: Any) -> ClientMessage | None:
    """Разобрать входящее сообщение по полю `type`. None — если невалидно."""
    if not isinstance(raw, dict):
        return None
    type_ = raw.get("type")
    if not isinstance(type_, str):
        return None
    model = _BY_TYPE.get(type_)
    if model is None:
        return None
    try:
        return model.model_validate(raw)  # type: ignore[return-value]
    except ValidationError:
        return None


# ---- Исходящие сообщения (хелперы) ----------------------------------------

def msg(type_: str, **payload: Any) -> dict[str, Any]:
    return {"type": type_, **payload}
