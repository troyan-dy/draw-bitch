from fastapi import APIRouter

from app.game.manager import manager
from app.schemas import CreateLobbyResponse, LobbyExistsResponse

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/lobby")
async def create_lobby() -> CreateLobbyResponse:
    """Создать пустое лобби. Дальше игроки входят по WebSocket."""
    lobby = manager.create()
    return CreateLobbyResponse(lobby_id=lobby.id)


@router.get("/lobby/{lobby_id}")
async def lobby_exists(lobby_id: str) -> LobbyExistsResponse:
    return LobbyExistsResponse(exists=manager.get(lobby_id) is not None)
