"use client";

import type { GameState } from "@/lib/types";

export default function Scoreboard({ state, me }: { state: GameState; me: string | null }) {
  const sorted = [...state.players].sort((a, b) => b.score - a.score);
  return (
    <div className="card scoreboard">
      {sorted.map((p) => (
        <div
          key={p.id}
          className={`score-row ${p.id === state.drawer_id ? "is-drawer" : ""}`}
        >
          <span className={`dot ${p.connected ? "" : "off"}`} />
          <span className="name">
            {p.name}
            {p.id === me ? " (ты)" : ""}
            {state.guessed.includes(p.id) ? " ✅" : ""}
          </span>
          <span className="pts">{p.score}</span>
        </div>
      ))}
    </div>
  );
}
