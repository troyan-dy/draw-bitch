from app.game.words import WORDS, pick_words


def test_words_pool_is_large_and_unique() -> None:
    assert len(WORDS) >= 200
    assert len(WORDS) == len(set(WORDS))


def test_pick_words_returns_unique_sample() -> None:
    words = pick_words(3)
    assert len(words) == 3
    assert len(set(words)) == 3
    assert all(w in WORDS for w in words)
