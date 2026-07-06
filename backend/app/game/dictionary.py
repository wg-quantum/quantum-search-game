"""Dictionary loading. Words are frequency-ordered; index = quantum state index."""

from functools import lru_cache
from pathlib import Path

WORDS_PATH = Path(__file__).resolve().parents[2] / "data" / "words.txt"


@lru_cache(maxsize=1)
def load_words() -> tuple[str, ...]:
    words = tuple(
        w.strip().lower() for w in WORDS_PATH.read_text().splitlines() if w.strip()
    )
    if not words:
        raise RuntimeError(f"empty dictionary at {WORDS_PATH}")
    return words


@lru_cache(maxsize=1)
def word_index() -> dict[str, int]:
    return {w: i for i, w in enumerate(load_words())}
