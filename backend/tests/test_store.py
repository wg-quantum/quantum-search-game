import random
import time

import pytest

from app.game.state import TTL_SECONDS, GameError, InMemoryGameStore


def _store() -> InMemoryGameStore:
    return InMemoryGameStore(rng=random.Random(1))


def test_get_unknown_game_raises_not_found():
    store = _store()
    with pytest.raises(GameError) as exc:
        store.get("does-not-exist")
    assert exc.value.code == "not_found"
    assert exc.value.status == 404


def test_idle_game_expires_after_ttl():
    store = _store()
    game = store.create()
    # Simulate the game sitting untouched past its TTL.
    game.last_seen = time.time() - TTL_SECONDS - 1
    with pytest.raises(GameError) as exc:
        store.get(game.game_id)
    assert exc.value.code == "not_found"


def test_get_refreshes_last_seen_sliding_ttl():
    store = _store()
    game = store.create()
    # Almost expired, but a get() within the window must revive the clock.
    game.last_seen = time.time() - TTL_SECONDS + 5
    got = store.get(game.game_id)
    assert got is game
    assert time.time() - got.last_seen < 1  # last_seen was refreshed to now


def test_create_evicts_expired_games():
    store = _store()
    stale = store.create()
    stale.last_seen = time.time() - TTL_SECONDS - 1
    # Creating a new game triggers eviction of the stale one.
    store.create()
    assert stale.game_id not in store._games
