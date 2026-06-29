"use client";

import { useEffect, useRef, useState } from "react";

import type { ChatLine, GameState } from "@/lib/types";

export default function Chat({
  state,
  me,
  lines,
  onSend,
}: {
  state: GameState;
  me: string | null;
  lines: ChatLine[];
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const nameById = (id?: string) =>
    state.players.find((p) => p.id === id)?.name ?? "?";

  // Рисующий и уже угадавшие не угадывают — но могут переписываться.
  const isDrawer = state.drawer_id === me;
  const hasGuessed = !!me && state.guessed.includes(me);
  const placeholder =
    state.phase === "drawing"
      ? isDrawer
        ? "Ты рисуешь — без подсказок 🤫"
        : hasGuessed
          ? "Ты угадал! Можешь болтать"
          : "Введи догадку…"
      : "Сообщение…";

  function submit() {
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  }

  return (
    <div className="card chat">
      <div className="chat-lines">
        {lines.map((l) => (
          <div key={l.id} className={`chat-line ${l.kind}`}>
            {l.kind === "chat" && <span className="who">{nameById(l.playerId)}: </span>}
            {l.kind === "correct" && (
              <span className="who">{nameById(l.playerId)} </span>
            )}
            {l.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="chat-input">
        <input
          maxLength={200}
          placeholder={placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
      </div>
    </div>
  );
}
