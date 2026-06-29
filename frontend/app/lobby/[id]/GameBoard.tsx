"use client";

import { useState } from "react";

import type { SocketApi } from "@/lib/useGameSocket";

import Canvas from "./Canvas";
import Chat from "./Chat";
import Scoreboard from "./Scoreboard";
import Timer from "./Timer";
import Toolbar, { SIZES } from "./Toolbar";

export default function GameBoard({ socket }: { socket: SocketApi }) {
  const { state, me, send, strokes, wordChoices, chat, lastWord } = socket;
  const [color, setColor] = useState("#000000");
  const [size, setSize] = useState(SIZES[1]);

  if (!state) return null;

  const isDrawer = state.drawer_id === me;
  const drawerName =
    state.players.find((p) => p.id === state.drawer_id)?.name ?? "Игрок";
  const canDraw = isDrawer && state.phase === "drawing";

  return (
    <main className="game">
      <div className="game-main">
        <div className="card topbar">
          <div>
            {state.phase === "drawing" ? (
              isDrawer && state.word ? (
                <span className="word-mask">{state.word}</span>
              ) : (
                <span className="word-mask">{state.word_mask}</span>
              )
            ) : state.phase === "game_end" ? (
              <span className="muted">Игра окончена</span>
            ) : (
              <span className="muted">
                Ход {Math.min(state.turn_index + 1, state.total_turns)} из {state.total_turns}
              </span>
            )}
          </div>
          <div className="muted" style={{ fontSize: 13 }}>
            {state.phase === "game_end" || !state.drawer_id
              ? ""
              : isDrawer
                ? "Ты рисуешь"
                : `Рисует ${drawerName}`}
          </div>
          <Timer seconds={state.time_left} active={state.phase === "drawing"} />
        </div>

        {canDraw && (
          <Toolbar
            color={color}
            size={size}
            onColor={setColor}
            onSize={setSize}
            onClear={() => send({ type: "clear" })}
          />
        )}

        <div className="canvas-wrap">
          <Canvas
            strokes={strokes}
            canDraw={canDraw}
            color={color}
            size={size}
            onSegment={(segment) => send({ type: "draw", segment })}
          />

          {state.phase === "choosing" && (
            <div className="overlay">
              {isDrawer ? (
                <>
                  <h2>Выбери слово</h2>
                  <div className="choices">
                    {wordChoices.map((w) => (
                      <button
                        key={w}
                        className="primary"
                        onClick={() => send({ type: "choose_word", word: w })}
                      >
                        {w}
                      </button>
                    ))}
                  </div>
                </>
              ) : (
                <h2>{drawerName} выбирает слово…</h2>
              )}
            </div>
          )}

          {state.phase === "turn_end" && (
            <div className="overlay">
              <h2>Ход окончен</h2>
              {lastWord && (
                <p>
                  Слово было: <b>{lastWord}</b>
                </p>
              )}
              <p className="muted">Следующий ход скоро начнётся…</p>
            </div>
          )}

          {state.phase === "game_end" && <GameEndOverlay socket={socket} />}
        </div>
      </div>

      <div className="sidebar">
        <Scoreboard state={state} me={me} />
        <Chat
          state={state}
          me={me}
          lines={chat}
          onSend={(text) => send({ type: "chat", text })}
        />
      </div>
    </main>
  );
}

function GameEndOverlay({ socket }: { socket: SocketApi }) {
  const { state, me, send } = socket;
  if (!state) return null;
  const isHost = state.host_id === me;
  const sorted = [...state.players].sort((a, b) => b.score - a.score);
  const winner = sorted[0];

  return (
    <div className="overlay">
      <h2>🏆 Игра окончена</h2>
      {winner && (
        <p>
          Победитель: <b>{winner.name}</b> ({winner.score})
        </p>
      )}
      <div style={{ width: "min(320px, 80%)", display: "flex", flexDirection: "column", gap: 6 }}>
        {sorted.map((p, i) => (
          <div className="score-row" key={p.id}>
            <span style={{ width: 20 }}>{i + 1}.</span>
            <span className="name">{p.name}</span>
            <span className="pts">{p.score}</span>
          </div>
        ))}
      </div>
      {isHost ? (
        <button className="primary" onClick={() => send({ type: "start_game" })}>
          Играть снова
        </button>
      ) : (
        <p className="muted">Ждём хоста для новой игры…</p>
      )}
    </div>
  );
}
