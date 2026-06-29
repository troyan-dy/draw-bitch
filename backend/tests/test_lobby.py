from app.game.lobby import Lobby, Phase, normalize


def _start_two_player_game(lobby: Lobby) -> tuple[str, str]:
    a = lobby.add_player("Аня").id
    b = lobby.add_player("Боря").id
    assert lobby.start_game(a) is True
    return a, b


def test_first_player_becomes_host(lobby: Lobby) -> None:
    a = lobby.add_player("Аня")
    lobby.add_player("Боря")
    assert lobby.host_id == a.id


def test_reconnect_by_player_id_keeps_score(lobby: Lobby) -> None:
    a = lobby.add_player("Аня")
    a.score = 50
    a.connected = False
    again = lobby.add_player("Аня", player_id=a.id)
    assert again.id == a.id
    assert again.connected is True
    assert again.score == 50
    assert len(lobby.players) == 1


def test_cannot_start_with_one_player(lobby: Lobby) -> None:
    a = lobby.add_player("Аня")
    assert lobby.start_game(a.id) is False


def test_non_host_cannot_start(lobby: Lobby) -> None:
    lobby.add_player("Аня")
    b = lobby.add_player("Боря")
    assert lobby.start_game(b.id) is False


def test_start_game_enters_choosing_with_choices(lobby: Lobby) -> None:
    _start_two_player_game(lobby)
    assert lobby.phase == Phase.CHOOSING
    assert len(lobby.word_choices) == 3
    assert lobby.drawer_id is not None


def test_choose_word_starts_drawing(lobby: Lobby) -> None:
    _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    assert drawer is not None
    word = lobby.word_choices[0]
    assert lobby.choose_word(drawer, word, now=0.0) is True
    assert lobby.phase == Phase.DRAWING
    assert lobby.word == word


def test_choose_word_rejects_wrong_word_or_player(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    other = b if drawer == a else a
    assert lobby.choose_word(other, lobby.word_choices[0], now=0.0) is False
    assert lobby.choose_word(drawer, "несуществующее", now=0.0) is False


def test_correct_guess_scores_and_hides_word(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    guesser = b if drawer == a else a
    word = lobby.word_choices[0]
    lobby.choose_word(drawer, word, now=0.0)
    result = lobby.submit_guess(guesser, word, now=1.0)
    assert result.correct is True
    assert result.points > 0
    assert lobby.players[guesser].score == result.points
    # Маска не раскрывает слово.
    assert lobby.word_mask() == " ".join("_" for _ in word)


def test_drawer_cannot_guess(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    assert drawer is not None
    word = lobby.word_choices[0]
    lobby.choose_word(drawer, word, now=0.0)
    result = lobby.submit_guess(drawer, word, now=1.0)
    assert result.correct is False


def test_guess_is_case_and_yo_insensitive(lobby: Lobby) -> None:
    assert normalize("ЁЖ") == normalize("еж")


def test_all_guessed_flag_when_everyone_guesses(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    guesser = b if drawer == a else a
    word = lobby.word_choices[0]
    lobby.choose_word(drawer, word, now=0.0)
    result = lobby.submit_guess(guesser, word, now=1.0)
    assert result.all_guessed is True


def test_double_guess_is_ignored(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    guesser = b if drawer == a else a
    word = lobby.word_choices[0]
    lobby.choose_word(drawer, word, now=0.0)
    lobby.submit_guess(guesser, word, now=1.0)
    second = lobby.submit_guess(guesser, word, now=2.0)
    assert second.already is True


def test_end_turn_awards_drawer_and_advance_cycles(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    lobby.total_turns = 2
    first_drawer = lobby.drawer_id
    word = lobby.word_choices[0]
    guesser = b if first_drawer == a else a
    lobby.choose_word(first_drawer, word, now=0.0)
    lobby.submit_guess(guesser, word, now=1.0)
    lobby.end_turn()
    assert lobby.phase == Phase.TURN_END
    assert lobby.players[first_drawer].score > 0  # бонус рисующему
    lobby.advance()
    assert lobby.phase == Phase.CHOOSING
    assert lobby.drawer_id != first_drawer  # следующий по очереди
    lobby.advance()  # после 2-го хода игра кончается
    assert lobby.phase == Phase.GAME_END


def test_drawer_left_during_turn_detected(lobby: Lobby) -> None:
    _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    assert drawer is not None
    assert lobby.drawer_left_during_turn(drawer) is True


def test_host_reassigned_when_host_leaves(lobby: Lobby) -> None:
    a = lobby.add_player("Аня")
    b = lobby.add_player("Боря")
    lobby.mark_offline(a.id)
    assert lobby.host_id == b.id


def test_time_left_counts_down(lobby: Lobby) -> None:
    _start_two_player_game(lobby)
    lobby.round_seconds = 80
    drawer = lobby.drawer_id
    assert drawer is not None
    lobby.choose_word(drawer, lobby.word_choices[0], now=100.0)
    assert lobby.time_left(now=110.0) == 70.0


def test_add_and_clear_strokes(lobby: Lobby) -> None:
    _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    assert drawer is not None
    lobby.choose_word(drawer, lobby.word_choices[0], now=0.0)
    seg = {"x0": 0.0, "y0": 0.0, "x1": 0.1, "y1": 0.1, "color": "#000", "size": 4.0}
    assert lobby.add_stroke(drawer, seg) is True
    assert len(lobby.strokes) == 1
    assert lobby.clear_canvas(drawer) is True
    assert lobby.strokes == []


def test_snapshot_reveals_word_only_to_drawer(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    drawer = lobby.drawer_id
    assert drawer is not None
    other = b if drawer == a else a
    word = lobby.word_choices[0]
    lobby.choose_word(drawer, word, now=0.0)
    assert lobby.snapshot(now=1.0, for_player=drawer)["word"] == word
    assert lobby.snapshot(now=1.0, for_player=other)["word"] is None


def test_start_game_resets_scores(lobby: Lobby) -> None:
    a, b = _start_two_player_game(lobby)
    lobby.players[a].score = 99
    lobby.phase = Phase.GAME_END
    lobby.start_game(lobby.host_id or a)
    assert lobby.players[a].score == 0
