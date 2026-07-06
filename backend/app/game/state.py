"""Game state and in-memory store (personal use; swappable via Protocol)."""

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.game.candidates import filter_candidates
from app.game.dictionary import load_words, word_index
from app.game.feedback import Feedback, Tile, compute_feedback

MAX_TURNS = 6
WORD_LENGTH = 5
TTL_SECONDS = 24 * 3600


class GameError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass
class GameState:
    game_id: str
    answer: str  # server-side only, never serialized to clients
    guesses: list[str] = field(default_factory=list)
    feedbacks: list[Feedback] = field(default_factory=list)
    status: str = "playing"  # playing | won | lost
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    _candidates: list[int] | None = field(default=None, init=False)  # cache
    # Serializes concurrent access to one game (FastAPI runs sync endpoints
    # on a thread pool, so the same game may be touched by two threads).
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False, compare=False
    )

    @property
    def turn(self) -> int:
        return len(self.guesses)

    @property
    def history(self) -> list[tuple[str, Feedback]]:
        return list(zip(self.guesses, self.feedbacks))

    def candidate_indices(self) -> list[int]:
        with self._lock:
            if self._candidates is None:
                self._candidates = filter_candidates(load_words(), self.history)
            return self._candidates

    def apply_guess(self, word: str) -> Feedback:
        word = word.strip().lower()
        with self._lock:
            if self.status != "playing":
                raise GameError("game_over", "game is already finished")
            if len(word) != WORD_LENGTH or not word.isalpha():
                raise GameError("invalid_word", f"guess must be {WORD_LENGTH} letters")
            if word not in word_index():
                raise GameError("unknown_word", f"'{word}' is not in the dictionary")

            fb = compute_feedback(self.answer, word)
            self.guesses.append(word)
            self.feedbacks.append(fb)
            self._candidates = None

            if all(t is Tile.GREEN for t in fb):
                self.status = "won"
            elif self.turn >= MAX_TURNS:
                self.status = "lost"
            return fb


class GameStore(Protocol):
    def create(self) -> GameState: ...
    def get(self, game_id: str) -> GameState: ...


class InMemoryGameStore:
    def __init__(self, rng: random.Random | None = None):
        self._games: dict[str, GameState] = {}
        self._rng = rng or random.Random()
        self._lock = threading.Lock()

    def create(self) -> GameState:
        with self._lock:
            self._evict_expired()
            game = GameState(
                game_id=str(uuid.uuid4()),
                answer=self._rng.choice(load_words()),
            )
            self._games[game.game_id] = game
            return game

    def get(self, game_id: str) -> GameState:
        now = time.time()
        with self._lock:
            game = self._games.get(game_id)
            # Sliding TTL: expiry is measured from last access, so an
            # actively-played game is never evicted mid-game.
            if game is None or now - game.last_seen > TTL_SECONDS:
                self._games.pop(game_id, None)
                raise GameError("not_found", "game not found", status=404)
            game.last_seen = now
            return game

    def _evict_expired(self) -> None:
        # Caller holds self._lock.
        now = time.time()
        expired = [k for k, g in self._games.items() if now - g.last_seen > TTL_SECONDS]
        for k in expired:
            self._games.pop(k, None)
