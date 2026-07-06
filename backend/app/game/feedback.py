"""Wordle feedback rules (official duplicate-letter handling).

Pass 1: mark exact-position matches (green) and consume those answer letters.
Pass 2: left to right, mark yellow while unconsumed answer letters remain.
"""

from collections import Counter
from enum import Enum


class Tile(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    GRAY = "gray"


Feedback = tuple[Tile, ...]


def compute_feedback(answer: str, guess: str) -> Feedback:
    if len(answer) != len(guess):
        raise ValueError("answer and guess must have equal length")

    answer = answer.lower()
    guess = guess.lower()
    result: list[Tile] = [Tile.GRAY] * len(guess)

    remaining = Counter()
    for a, g in zip(answer, guess):
        if a == g:
            pass  # green, letter consumed
        else:
            remaining[a] += 1

    for i, (a, g) in enumerate(zip(answer, guess)):
        if a == g:
            result[i] = Tile.GREEN
        elif remaining[g] > 0:
            result[i] = Tile.YELLOW
            remaining[g] -= 1

    return tuple(result)
