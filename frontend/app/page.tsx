"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createLobby } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [joinValue, setJoinValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onCreate() {
    setCreating(true);
    setError(null);
    try {
      const id = await createLobby();
      router.push(`/lobby/${id}`);
    } catch {
      setError("Не удалось создать лобби. Бэкенд доступен?");
      setCreating(false);
    }
  }

  function onJoin() {
    const trimmed = joinValue.trim();
    if (!trimmed) return;
    // Принимаем как полную ссылку, так и просто код лобби.
    const match = trimmed.match(/lobby\/([a-z0-9]+)/i);
    const id = match ? match[1] : trimmed;
    router.push(`/lobby/${id}`);
  }

  return (
    <main className="home">
      <div className="card home-card">
        <h1 className="brand">draw-bitch</h1>
        <p className="muted">
          Рисуй загаданное слово — друзья угадывают в чате. Кто быстрее, тот и в дамках.
        </p>

        <div className="home-actions">
          <button className="primary" onClick={onCreate} disabled={creating}>
            {creating ? "Создаём…" : "Создать лобби"}
          </button>
          {error && <span style={{ color: "var(--danger)", fontSize: 14 }}>{error}</span>}
        </div>

        <div className="divider">или войти по ссылке</div>

        <div className="row">
          <input
            placeholder="Вставь ссылку или код лобби"
            value={joinValue}
            onChange={(e) => setJoinValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onJoin()}
          />
          <button onClick={onJoin} disabled={!joinValue.trim()}>
            Войти
          </button>
        </div>
      </div>
    </main>
  );
}
