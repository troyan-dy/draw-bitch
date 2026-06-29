from app.game import scoring


def test_faster_guess_scores_more() -> None:
    fast = scoring.guesser_points(time_left=90, duration=100, order=0, base=100, minimum=20)
    slow = scoring.guesser_points(time_left=10, duration=100, order=0, base=100, minimum=20)
    assert fast > slow


def test_guess_at_end_gives_minimum_floor() -> None:
    pts = scoring.guesser_points(time_left=0, duration=100, order=5, base=100, minimum=20)
    assert pts >= 20


def test_zero_duration_safe() -> None:
    assert scoring.guesser_points(time_left=0, duration=0, order=0, base=100, minimum=20) == 100


def test_first_guesser_gets_rank_bonus() -> None:
    first = scoring.guesser_points(time_left=50, duration=100, order=0, base=100, minimum=20)
    third = scoring.guesser_points(time_left=50, duration=100, order=2, base=100, minimum=20)
    assert first > third


def test_drawer_points_scale_with_guessers() -> None:
    full = scoring.drawer_points(num_guessed=3, num_potential=3, base=60)
    half = scoring.drawer_points(num_guessed=1, num_potential=3, base=60)
    assert full == 60
    assert 0 < half < full


def test_drawer_points_no_potential_is_zero() -> None:
    assert scoring.drawer_points(num_guessed=0, num_potential=0, base=60) == 0
