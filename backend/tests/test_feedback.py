import pytest

from app.game.feedback import Tile, compute_feedback

G, Y, X = Tile.GREEN, Tile.YELLOW, Tile.GRAY


@pytest.mark.parametrize(
    "answer,guess,expected",
    [
        # exact match
        ("crane", "crane", (G, G, G, G, G)),
        # no overlap
        ("crane", "podgy", (X, X, X, X, X)),
        # simple yellow
        ("crane", "acorn", (Y, Y, X, Y, Y)),
        # duplicate in guess, single in answer: only first gets yellow
        ("speed", "erase", (Y, X, X, Y, Y)),
        # duplicate in guess, double in answer: both yellow
        ("speed", "eerie", (Y, Y, X, X, X)),
        # green consumes: second 'e' in guess has no remaining match
        ("abide", "keeps", (X, Y, X, X, X)),
        # green + extra duplicate is gray
        ("maxim", "mamma", (G, G, Y, X, X)),
        # yellow before green position still yellow, dup handled
        ("aroma", "adapt", (G, X, Y, X, X)),
    ],
)
def test_compute_feedback(answer, guess, expected):
    assert compute_feedback(answer, guess) == expected


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        compute_feedback("crane", "cranes")


def test_case_insensitive():
    assert compute_feedback("CRANE", "crane") == (G, G, G, G, G)
