"""Чистые функции подсчёта очков. Без I/O — легко тестировать."""

# Бонус за место в очереди угадывания: первому +RANK_BONUS_MAX, дальше минус STEP за место.
RANK_BONUS_MAX = 10
RANK_BONUS_STEP = 2


def guesser_points(
    time_left: float,
    duration: float,
    order: int,
    base: int,
    minimum: int,
) -> int:
    """Очки угадавшему.

    Чем больше осталось времени (раньше угадал) — тем больше очков: линейно от
    `base` (мгновенно) до `minimum` (у самого конца таймера). Плюс небольшой
    бонус за место в очереди угадывания: первый угадавший получает чуть больше.

    `order` — порядковый номер угадывания, начиная с 0 (0 = угадал первым).
    """
    if duration <= 0:
        return base
    fraction = max(0, min(1, time_left / duration))
    speed = minimum + (base - minimum) * fraction
    # Бонус за место: первым +10%, дальше затухает.
    rank_bonus = max(0, RANK_BONUS_MAX - order * RANK_BONUS_STEP)
    return round(speed + rank_bonus)


def drawer_points(num_guessed: int, num_potential: int, base: int) -> int:
    """Бонус рисующему: пропорционально доле угадавших.

    `num_potential` — сколько игроков в принципе могли угадать (все, кроме
    самого рисующего). Если угадали все — рисующий получает `base`.
    """
    if num_potential <= 0:
        return 0
    fraction = num_guessed / num_potential
    return round(base * fraction)
