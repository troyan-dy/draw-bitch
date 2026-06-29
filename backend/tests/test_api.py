from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_lobby_then_exists() -> None:
    resp = client.post("/api/lobby")
    assert resp.status_code == 200
    lobby_id = resp.json()["lobby_id"]
    assert isinstance(lobby_id, str) and lobby_id

    check = client.get(f"/api/lobby/{lobby_id}")
    assert check.json() == {"exists": True}


def test_unknown_lobby_does_not_exist() -> None:
    resp = client.get("/api/lobby/zzzzzz")
    assert resp.json() == {"exists": False}


def test_ws_join_returns_player_id() -> None:
    lobby_id = client.post("/api/lobby").json()["lobby_id"]
    with client.websocket_connect(f"/ws/{lobby_id}") as ws:
        ws.send_json({"type": "join", "name": "Аня"})
        # Первое сообщение — joined с выданным player_id.
        joined = ws.receive_json()
        assert joined["type"] == "joined"
        assert joined["player_id"]
        # Затем приходит снимок состояния.
        state = ws.receive_json()
        assert state["type"] == "state"
        assert state["phase"] == "waiting"
        assert len(state["players"]) == 1


def test_ws_unknown_lobby_errors() -> None:
    with client.websocket_connect("/ws/zzzzzz") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
