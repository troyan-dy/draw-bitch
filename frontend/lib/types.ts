// Типы игрового состояния и сообщений — зеркало backend (app/schemas.py, Lobby.snapshot).

export type Phase = "waiting" | "choosing" | "drawing" | "turn_end" | "game_end";

export interface Player {
  id: string;
  name: string;
  score: number;
  connected: boolean;
}

export interface Segment {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  color: string;
  size: number;
}

// Полный снимок состояния лобби (сообщение "state").
export interface GameState {
  phase: Phase;
  host_id: string | null;
  drawer_id: string | null;
  round_seconds: number;
  total_turns: number;
  turn_index: number;
  time_left: number;
  word_mask: string;
  word: string | null; // не null только для рисующего/угадавших
  guessed: string[];
  strokes: Segment[];
  players: Player[];
}

// Запись в чате (включая системные сообщения об угадывании).
export interface ChatLine {
  id: number;
  kind: "chat" | "correct" | "system";
  playerId?: string;
  name?: string;
  text: string;
}

// ---- Исходящие сообщения (клиент → сервер) ----

export type ClientMessage =
  | { type: "join"; name: string; player_id: string | null }
  | { type: "start_game" }
  | { type: "update_settings"; round_seconds: number; total_turns: number }
  | { type: "choose_word"; word: string }
  | { type: "draw"; segment: Segment }
  | { type: "clear" }
  | { type: "chat"; text: string };

// ---- Входящие сообщения (сервер → клиент) ----

export type ServerMessage =
  | { type: "joined"; player_id: string }
  | ({ type: "state" } & GameState)
  | { type: "word_choices"; words: string[] }
  | { type: "draw"; segment: Segment }
  | { type: "clear" }
  | { type: "chat"; player_id: string; text: string }
  | { type: "correct_guess"; player_id: string; points: number }
  | { type: "turn_end"; word: string | null; scores: Record<string, number> }
  | { type: "game_end" }
  | { type: "error"; message: string };
