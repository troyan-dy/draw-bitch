import pytest

from app.game.lobby import Lobby


@pytest.fixture
def lobby() -> Lobby:
    return Lobby(id="test")
