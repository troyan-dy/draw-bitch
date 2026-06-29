"""Машина состояний одного лобби. Чистая логика игры без сети и таймеров.

Транспорт (`ws.py`) дёргает методы и рассылает то, что они возвращают; реальное
время передаётся аргументом `now`, чтобы логика оставалась детерминированной и
тестируемой.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from app.config import settings
from app.game import scoring
from app.game.words import pick_words


class Phase(StrEnum):
    WAITING = "waiting"  # ждём игроков, хост настраивает
    CHOOSING = "choosing"  # рисующий выбирает слово из 3
    DRAWING = "drawing"  # рисует, остальные угадывают
    TURN_END = "turn_end"  # показали слово, начислили очки, пауза
    GAME_END = "game_end"  # итоговая таблица, пауза


@dataclass
class Player:
    id: str
    name: str
    score: int = 0
    connected: bool = True


def normalize(text: str) -> str:
    """Нормализация для сравнения догадки со словом."""
    return text.strip().lower().replace("ё", "е")


@dataclass
class GuessResult:
    correct: bool
    points: int = 0  # начислено угадавшему
    already: bool = False  # уже угадывал раньше / он рисующий
    all_guessed: bool = False  # после этой догадки угадали все, кого ждали


@dataclass
class Lobby:
    id: str
    phase: Phase = Phase.WAITING
    players: dict[str, Player] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)  # очерёдность по player_id
    host_id: str | None = None

    # Настройки игры.
    round_seconds: int = settings.round_seconds_default
    total_turns: int = settings.total_turns_default

    # Текущая игра/ход.
    turn_index: int = 0  # номер текущего хода, 0-based
    drawer_id: str | None = None
    word: str | None = None
    word_choices: list[str] = field(default_factory=list)
    guessed: set[str] = field(default_factory=set)  # кто угадал в этом ходу
    guess_order: int = 0  # сколько уже угадали (для бонуса за место)
    started_at: float | None = None  # время старта хода (DRAWING)
    strokes: list[dict] = field(default_factory=list)  # накопленный рисунок

    # ---- Игроки -----------------------------------------------------------

    def add_player(self, name: str, player_id: str | None = None) -> Player:
        """Добавить нового или вернуть существующего (реконнект по player_id)."""
        if player_id and player_id in self.players:
            player = self.players[player_id]
            player.connected = True
            if name:
                player.name = name
            return player

        pid = player_id or uuid.uuid4().hex
        player = Player(id=pid, name=name or "Гость")
        self.players[pid] = player
        self.order.append(pid)
        if self.host_id is None:
            self.host_id = pid
        return player

    def mark_offline(self, player_id: str) -> None:
        """Игрок отключился: помечаем оффлайн, но не удаляем (очки и место живут)."""
        player = self.players.get(player_id)
        if player:
            player.connected = False
        if player_id == self.host_id:
            self._reassign_host()

    def _reassign_host(self) -> None:
        """Передать роль хоста первому онлайн-игроку (или None, если все ушли)."""
        for pid in self.order:
            if self.players[pid].connected:
                self.host_id = pid
                return
        self.host_id = None

    @property
    def online_ids(self) -> list[str]:
        return [pid for pid in self.order if self.players[pid].connected]

    @property
    def empty(self) -> bool:
        return all(not p.connected for p in self.players.values())

    # ---- Жизненный цикл игры ---------------------------------------------

    def can_start(self, player_id: str) -> bool:
        return (
            self.phase in (Phase.WAITING, Phase.GAME_END)
            and player_id == self.host_id
            and len(self.online_ids) >= settings.min_players_to_start
        )

    def update_settings(self, player_id: str, round_seconds: int, total_turns: int) -> bool:
        """Хост меняет настройки в зале ожидания. Значения зажимаются в границы."""
        if player_id != self.host_id or self.phase not in (Phase.WAITING, Phase.GAME_END):
            return False
        self.round_seconds = max(
            settings.round_seconds_min, min(settings.round_seconds_max, round_seconds)
        )
        self.total_turns = max(
            settings.total_turns_min, min(settings.total_turns_max, total_turns)
        )
        return True

    def start_game(self, player_id: str) -> bool:
        """Начать игру: сбросить очки, зафиксировать очередь, открыть выбор слова."""
        if not self.can_start(player_id):
            return False
        for p in self.players.values():
            p.score = 0
        # Очередь рисующих = онлайн-игроки на момент старта.
        self.order = self.online_ids + [
            pid for pid in self.order if pid not in set(self.online_ids)
        ]
        self.turn_index = 0
        self._begin_turn()
        return True

    def _begin_turn(self) -> None:
        """Открыть фазу выбора слова для текущего рисующего."""
        self.drawer_id = self._drawer_for_turn(self.turn_index)
        self.word = None
        self.word_choices = pick_words(3)
        self.guessed.clear()
        self.guess_order = 0
        self.started_at = None
        self.strokes.clear()
        self.phase = Phase.CHOOSING

    def _drawer_for_turn(self, turn_index: int) -> str | None:
        """Рисующий выбирается циклически среди онлайн-игроков на старте игры."""
        candidates = self.online_ids or self.order
        if not candidates:
            return None
        return candidates[turn_index % len(candidates)]

    def choose_word(self, player_id: str, word: str, now: float) -> bool:
        """Текущий рисующий выбрал слово → начинается рисование и таймер."""
        if (
            self.phase != Phase.CHOOSING
            or player_id != self.drawer_id
            or word not in self.word_choices
        ):
            return False
        self.word = word
        self.started_at = now
        self.phase = Phase.DRAWING
        return True

    def time_left(self, now: float) -> float:
        if self.phase != Phase.DRAWING or self.started_at is None:
            return 0.0
        return max(0.0, self.round_seconds - (now - self.started_at))

    @property
    def potential_guessers(self) -> int:
        """Сколько игроков должны угадать, чтобы ход закрылся (все, кроме рисующего)."""
        return max(0, len(self.online_ids) - 1)

    def submit_guess(self, player_id: str, text: str, now: float) -> GuessResult:
        """Обработать сообщение в чате как догадку.

        Возвращает GuessResult. Если не угадал — correct=False (сообщение покажется
        в чате как обычно). Если угадал — текст скрывается вызывающим транспортом.
        """
        if (
            self.phase != Phase.DRAWING
            or player_id == self.drawer_id
            or player_id not in self.players
        ):
            return GuessResult(correct=False)
        if player_id in self.guessed:
            return GuessResult(correct=False, already=True)
        if self.word is None or normalize(text) != normalize(self.word):
            return GuessResult(correct=False)

        time_left = self.time_left(now)
        points = scoring.guesser_points(
            time_left=time_left,
            duration=float(self.round_seconds),
            order=self.guess_order,
            base=settings.guesser_base,
            minimum=settings.guesser_min,
        )
        self.players[player_id].score += points
        self.guessed.add(player_id)
        self.guess_order += 1
        all_guessed = len(self.guessed) >= self.potential_guessers
        return GuessResult(correct=True, points=points, all_guessed=all_guessed)

    def end_turn(self) -> None:
        """Завершить ход: начислить бонус рисующему, перейти в TURN_END."""
        if self.drawer_id and self.drawer_id in self.players:
            bonus = scoring.drawer_points(
                num_guessed=len(self.guessed),
                num_potential=self.potential_guessers,
                base=settings.drawer_base,
            )
            self.players[self.drawer_id].score += bonus
        self.phase = Phase.TURN_END

    def advance(self) -> None:
        """После паузы TURN_END: следующий ход или конец игры."""
        self.turn_index += 1
        if self.turn_index >= self.total_turns:
            self.phase = Phase.GAME_END
            self.drawer_id = None
            self.word = None
            self.word_choices = []
            self.strokes.clear()
        else:
            self._begin_turn()

    def drawer_left_during_turn(self, player_id: str) -> bool:
        """Отвалился ли рисующий во время своего хода (нужно завершить досрочно)."""
        return player_id == self.drawer_id and self.phase in (Phase.CHOOSING, Phase.DRAWING)

    # ---- Рисование --------------------------------------------------------

    def add_stroke(self, player_id: str, segment: dict) -> bool:
        if self.phase != Phase.DRAWING or player_id != self.drawer_id:
            return False
        self.strokes.append(segment)
        return True

    def clear_canvas(self, player_id: str) -> bool:
        if self.phase != Phase.DRAWING or player_id != self.drawer_id:
            return False
        self.strokes.clear()
        return True

    # ---- Снимок состояния -------------------------------------------------

    def word_mask(self) -> str:
        """Маска слова для угадывающих: подчёркивания, пробелы сохраняются."""
        if not self.word:
            return ""
        return " ".join("_" if ch != " " else " " for ch in self.word)

    def snapshot(self, now: float, *, for_player: str | None = None) -> dict:
        """Полное состояние для рассылки. Рисующему/угадавшим видно слово."""
        knows_word = (
            for_player is not None
            and (for_player == self.drawer_id or for_player in self.guessed)
        )
        return {
            "phase": self.phase.value,
            "host_id": self.host_id,
            "drawer_id": self.drawer_id,
            "round_seconds": self.round_seconds,
            "total_turns": self.total_turns,
            "turn_index": self.turn_index,
            "time_left": round(self.time_left(now), 1),
            "word_mask": self.word_mask(),
            "word": self.word if (knows_word and self.phase != Phase.WAITING) else None,
            "guessed": sorted(self.guessed),
            "strokes": self.strokes,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "score": p.score,
                    "connected": p.connected,
                }
                for p in (self.players[pid] for pid in self.order if pid in self.players)
            ],
        }
