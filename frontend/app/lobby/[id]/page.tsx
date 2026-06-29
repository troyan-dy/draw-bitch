"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useGameSocket } from "@/lib/useGameSocket";

import GameBoard from "./GameBoard";
import WaitingRoom from "./WaitingRoom";

const NAME_KEY = "drawbitch:name";

export default function LobbyPage() {
  const params = useParams<{ id: string }>();
  const lobbyId = params.id;

  const [name, setName] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [ready, setReady] = useState(false);

  // Подтягиваем сохранённое имя из прошлой сессии.
  useEffect(() => {
    const saved = localStorage.getItem(NAME_KEY);
    if (saved) {
      setDraft(saved);
    }
    setReady(true);
  }, []);

  function confirmName() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    localStorage.setItem(NAME_KEY, trimmed);
    setName(trimmed);
  }

  if (!ready) return null;

  if (!name) {
    return (
      <main className="name-screen">
        <div className="card home-card">
          <h2>Как тебя звать?</h2>
          <p className="muted">Имя увидят другие игроки в лобби.</p>
          <input
            autoFocus
            maxLength={24}
            placeholder="Имя"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && confirmName()}
          />
          <button className="primary" onClick={confirmName} disabled={!draft.trim()}>
            Войти в лобби
          </button>
        </div>
      </main>
    );
  }

  return <LobbyConnected lobbyId={lobbyId} name={name} />;
}

function LobbyConnected({ lobbyId, name }: { lobbyId: string; name: string }) {
  const socket = useGameSocket(lobbyId, name);
  const { state, error } = socket;

  if (error && !state) {
    return (
      <main className="center-screen">
        <div className="card home-card">
          <h2>Упс</h2>
          <p className="muted">{error}</p>
          <a href="/">
            <button className="primary">На главную</button>
          </a>
        </div>
      </main>
    );
  }

  if (!state) {
    return (
      <main className="center-screen">
        <p className="muted">Подключаемся к лобби…</p>
      </main>
    );
  }

  if (state.phase === "waiting") {
    return <WaitingRoom lobbyId={lobbyId} socket={socket} />;
  }

  return <GameBoard socket={socket} />;
}
