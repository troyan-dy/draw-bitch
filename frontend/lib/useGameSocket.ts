"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { wsUrl } from "./api";
import type { ChatLine, ClientMessage, GameState, Segment, ServerMessage } from "./types";

export interface SocketApi {
  state: GameState | null;
  me: string | null; // мой player_id
  connected: boolean;
  wordChoices: string[]; // непусто, когда мне предлагают выбрать слово
  chat: ChatLine[];
  strokes: Segment[]; // текущий рисунок (снимок + инкременты)
  lastWord: string | null; // слово прошлого хода (для экрана turn_end)
  error: string | null;
  send: (msg: ClientMessage) => void;
  clearWordChoices: () => void;
}

function pidKey(lobbyId: string): string {
  return `drawbitch:pid:${lobbyId}`;
}

export function useGameSocket(lobbyId: string, name: string | null): SocketApi {
  const [state, setState] = useState<GameState | null>(null);
  const [me, setMe] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [wordChoices, setWordChoices] = useState<string[]>([]);
  const [chat, setChat] = useState<ChatLine[]>([]);
  const [strokes, setStrokes] = useState<Segment[]>([]);
  const [lastWord, setLastWord] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptsRef = useRef(0);
  const closedRef = useRef(false);
  const chatIdRef = useRef(0);
  const nameRef = useRef(name);
  nameRef.current = name;

  const pushChat = useCallback((line: Omit<ChatLine, "id">) => {
    setChat((prev) => {
      const next = [...prev, { ...line, id: chatIdRef.current++ }];
      return next.length > 200 ? next.slice(-200) : next;
    });
  }, []);

  const send = useCallback((msg: ClientMessage) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  const clearWordChoices = useCallback(() => setWordChoices([]), []);

  useEffect(() => {
    if (!name) return;
    closedRef.current = false;

    const connect = () => {
      const ws = new WebSocket(wsUrl(lobbyId));
      wsRef.current = ws;

      ws.onopen = () => {
        attemptsRef.current = 0;
        setConnected(true);
        const stored =
          typeof window !== "undefined" ? localStorage.getItem(pidKey(lobbyId)) : null;
        send({ type: "join", name: nameRef.current ?? "", player_id: stored });
      };

      ws.onmessage = (ev) => {
        let msg: ServerMessage;
        try {
          msg = JSON.parse(ev.data) as ServerMessage;
        } catch {
          return;
        }
        handle(msg);
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (closedRef.current) return;
        attemptsRef.current += 1;
        const delay = Math.min(1000 * 2 ** attemptsRef.current, 8000);
        reconnectRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    };

    const handle = (msg: ServerMessage) => {
      switch (msg.type) {
        case "joined":
          setMe(msg.player_id);
          if (typeof window !== "undefined") {
            localStorage.setItem(pidKey(lobbyId), msg.player_id);
          }
          break;
        case "state": {
          const { type, ...gs } = msg;
          void type;
          setState(gs);
          setStrokes(gs.strokes);
          break;
        }
        case "word_choices":
          setWordChoices(msg.words);
          break;
        case "draw":
          setStrokes((prev) => [...prev, msg.segment]);
          break;
        case "clear":
          setStrokes([]);
          break;
        case "chat":
          pushChat({ kind: "chat", playerId: msg.player_id, text: msg.text });
          break;
        case "correct_guess":
          pushChat({ kind: "correct", playerId: msg.player_id, text: "угадал слово!" });
          break;
        case "turn_end":
          if (msg.word) setLastWord(msg.word);
          setWordChoices([]);
          if (msg.word) {
            pushChat({ kind: "system", text: `Слово было: ${msg.word}` });
          }
          break;
        case "game_end":
          setWordChoices([]);
          pushChat({ kind: "system", text: "Игра окончена!" });
          break;
        case "error":
          setError(msg.message);
          break;
      }
    };

    connect();

    return () => {
      closedRef.current = true;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [lobbyId, name, send, pushChat]);

  return {
    state,
    me,
    connected,
    wordChoices,
    chat,
    strokes,
    lastWord,
    error,
    send,
    clearWordChoices,
  };
}
