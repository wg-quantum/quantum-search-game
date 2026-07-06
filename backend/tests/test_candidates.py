from app.game.candidates import filter_candidates, is_consistent
from app.game.dictionary import load_words
from app.game.feedback import compute_feedback


def test_no_history_returns_all():
    words = load_words()
    assert filter_candidates(words, []) == list(range(len(words)))


def test_answer_always_survives():
    words = load_words()
    answer = "brave"
    history = [(g, compute_feedback(answer, g)) for g in ["crane", "boils", "brave"]]
    indices = filter_candidates(words, history)
    assert words.index(answer) in indices


def test_all_survivors_are_consistent():
    words = load_words()
    answer = "sweet"
    history = [(g, compute_feedback(answer, g)) for g in ["crane", "sleep"]]
    indices = filter_candidates(words, history)
    assert indices, "candidate set must not be empty while answer is in dictionary"
    for i in indices:
        assert is_consistent(words[i], history)


def test_filtering_shrinks_monotonically():
    words = load_words()
    answer = "pound"
    history: list = []
    prev = len(words)
    for guess in ["crane", "moist", "pound"]:
        history.append((guess, compute_feedback(answer, guess)))
        cur = len(filter_candidates(words, history))
        assert cur <= prev
        prev = cur
    assert prev == 1  # only the answer remains after guessing it
