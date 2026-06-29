"use client";

import { useEffect, useState } from "react";

// Локальный обратный отсчёт: стартует от state.time_left и тикает каждую секунду,
// чтобы не зависеть от частоты обновлений с сервера.

export default function Timer({ seconds, active }: { seconds: number; active: boolean }) {
  const [left, setLeft] = useState(seconds);

  useEffect(() => {
    setLeft(seconds);
  }, [seconds]);

  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      setLeft((v) => Math.max(0, v - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [active]);

  const shown = Math.ceil(left);
  return (
    <div className={`timer ${active && shown <= 10 ? "low" : ""}`}>{active ? shown : "—"}</div>
  );
}
