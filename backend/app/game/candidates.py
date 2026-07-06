"""Candidate filtering.

A word is a candidate iff, for every past (guess, feedback) pair, assuming
that word were the answer would have produced exactly that feedback.
This set is what the quantum oracle will mark in Phase 3.
"""

from app.game.feedback import Feedback, compute_feedback


def is_consistent(word: str, history: list[tuple[str, Feedback]]) -> bool:
    return all(compute_feedback(word, guess) == fb for guess, fb in history)


def filter_candidates(
    words: tuple[str, ...], history: list[tuple[str, Feedback]]
) -> list[int]:
    """Return dictionary indices of all words consistent with the history."""
    return [i for i, w in enumerate(words) if is_consistent(w, history)]
