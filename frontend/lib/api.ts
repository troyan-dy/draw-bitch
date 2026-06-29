// REST- и WebSocket-адреса бэкенда.
//
// NEXT_PUBLIC_BACKEND_URL пуст → тот же origin (прод: nginx роутит /api и /ws на
// бэкенд). В дев-режиме задаём http://localhost:8000.

function backendBase(): string {
  const env = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (env) return env.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

export function wsUrl(lobbyId: string): string {
  const base = backendBase();
  const httpUrl = base || (typeof window !== "undefined" ? window.location.origin : "");
  const proto = httpUrl.startsWith("https") ? "wss" : "ws";
  const host = httpUrl.replace(/^https?:\/\//, "");
  return `${proto}://${host}/ws/${lobbyId}`;
}

export async function createLobby(): Promise<string> {
  const resp = await fetch(`${backendBase()}/api/lobby`, { method: "POST" });
  if (!resp.ok) throw new Error("Не удалось создать лобби");
  const data = (await resp.json()) as { lobby_id: string };
  return data.lobby_id;
}

export async function lobbyExists(lobbyId: string): Promise<boolean> {
  try {
    const resp = await fetch(`${backendBase()}/api/lobby/${lobbyId}`);
    if (!resp.ok) return false;
    const data = (await resp.json()) as { exists: boolean };
    return data.exists;
  } catch {
    return false;
  }
}
