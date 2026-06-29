from app.game.manager import LobbyManager


def test_create_gives_unique_ids() -> None:
    m = LobbyManager()
    a = m.create()
    b = m.create()
    assert a.id != b.id
    assert len(a.id) == 6


def test_get_missing_returns_none() -> None:
    m = LobbyManager()
    assert m.get("nope") is None


def test_get_and_remove() -> None:
    m = LobbyManager()
    lobby = m.create()
    assert m.get(lobby.id) is lobby
    m.remove(lobby.id)
    assert m.get(lobby.id) is None
