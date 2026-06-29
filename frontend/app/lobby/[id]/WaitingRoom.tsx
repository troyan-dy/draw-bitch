"use client";

import { useEffect, useState } from "react";

import type { SocketApi } from "@/lib/useGameSocket";

export default function WaitingRoom({
  lobbyId,
  socket,
}: {
  lobbyId: string;
  socket: SocketApi;
}) {
  const { state, me, send } = socket;
  const [copied, setCopied] = useState(false);

  const isHost = !!me && state?.host_id === me;
  const players = state?.players ?? [];
  const canStart = players.filter((p) => p.connected).length >= 2;

  // Локальные поля настроек, синхронизированные с состоянием от сервера.
  const [seconds, setSeconds] = useState(state?.round_seconds ?? 80);
  const [turns, setTurns] = useState(state?.total_turns ?? 6);
  useEffect(() => {
    if (state) {
      setSeconds(state.round_seconds);
      setTurns(state.total_turns);
    }
  }, [state?.round_seconds, state?.total_turns]); // eslint-disable-line react-hooks/exhaustive-deps

  function pushSettings(nextSeconds: number, nextTurns: number) {
    setSeconds(nextSeconds);
    setTurns(nextTurns);
    send({ type: "update_settings", round_seconds: nextSeconds, total_turns: nextTurns });
  }

  const inviteUrl =
    typeof window !== "undefined" ? `${window.location.origin}/lobby/${lobbyId}` : "";

  async function copyInvite() {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* буфер недоступен — пользователь скопирует вручную */
    }
  }

  return (
    <main className="waiting">
      <h1 className="brand" style={{ fontSize: 32 }}>
        Лобби
      </h1>

      <div className="card" style={{ padding: 18 }}>
        <div className="field" style={{ marginBottom: 12 }}>
          <label>Ссылка-приглашение</label>
          <div className="invite">
            <input readOnly value={inviteUrl} onFocus={(e) => e.target.select()} />
            <button onClick={copyInvite}>{copied ? "Скопировано" : "Копировать"}</button>
          </div>
        </div>

        <div className="settings-grid">
          <div className="field">
            <label>Секунд на ход</label>
            <input
              type="number"
              min={20}
              max={180}
              value={seconds}
              disabled={!isHost}
              onChange={(e) => pushSettings(Number(e.target.value), turns)}
            />
          </div>
          <div className="field">
            <label>Сколько ходов (рисующих)</label>
            <input
              type="number"
              min={1}
              max={30}
              value={turns}
              disabled={!isHost}
              onChange={(e) => pushSettings(seconds, Number(e.target.value))}
            />
          </div>
        </div>
        {!isHost && (
          <p className="muted" style={{ fontSize: 13, marginTop: 10 }}>
            Настройки задаёт хост.
          </p>
        )}
      </div>

      <div className="card" style={{ padding: 18 }}>
        <h3 style={{ marginBottom: 12 }}>Игроки ({players.length})</h3>
        <div className="players-list">
          {players.map((p) => (
            <div className="player-row" key={p.id}>
              <span className={`dot ${p.connected ? "" : "off"}`} />
              <span style={{ flex: 1 }}>{p.name}</span>
              {p.id === state?.host_id && <span className="badge">хост</span>}
              {p.id === me && <span className="badge">ты</span>}
            </div>
          ))}
        </div>
      </div>

      {isHost ? (
        <button
          className="primary"
          style={{ fontSize: 18, padding: "14px" }}
          disabled={!canStart}
          onClick={() => send({ type: "start_game" })}
        >
          {canStart ? "Старт" : "Нужно ≥2 игроков"}
        </button>
      ) : (
        <p className="muted" style={{ textAlign: "center" }}>
          Ждём, пока хост начнёт игру…
        </p>
      )}
    </main>
  );
}
