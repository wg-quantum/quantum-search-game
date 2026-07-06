import random

import pytest
from fastapi.testclient import TestClient

from app.game.state import InMemoryGameStore
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    # seeded RNG -> deterministic answer for reproducible tests
    app = create_app(store=InMemoryGameStore(rng=random.Random(42)))
    return TestClient(app)


def _create(client: TestClient) -> str:
    res = client.post("/api/v1/games")
    assert res.status_code == 201
    body = res.json()
    assert body["max_turns"] == 6
    assert body["word_length"] == 5
    assert body["dictionary_size"] == 2315
    return body["game_id"]


def _answer(client: TestClient, game_id: str) -> str:
    return client.app.state.store.get(game_id).answer


def test_full_game_win(client: TestClient):
    game_id = _create(client)
    answer = _answer(client, game_id)

    res = client.post(f"/api/v1/games/{game_id}/guesses", json={"word": "crane"})
    assert res.status_code == 200
    body = res.json()
    assert len(body["feedback"]) == 5
    assert body["candidate_count"] >= 1

    res = client.post(f"/api/v1/games/{game_id}/guesses", json={"word": answer})
    body = res.json()
    assert body["status"] == "won"
    assert body["feedback"] == ["green"] * 5
    assert body["candidate_count"] == 1


def test_lose_after_max_turns(client: TestClient):
    game_id = _create(client)
    answer = _answer(client, game_id)
    wrong = next(w for w in ["crane", "pound"] if w != answer)
    for _ in range(6):
        res = client.post(f"/api/v1/games/{game_id}/guesses", json={"word": wrong})
    assert res.json()["status"] == "lost"
    # further guesses rejected
    res = client.post(f"/api/v1/games/{game_id}/guesses", json={"word": wrong})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "game_over"


def test_unknown_word_rejected(client: TestClient):
    game_id = _create(client)
    res = client.post(f"/api/v1/games/{game_id}/guesses", json={"word": "zzzzz"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "unknown_word"


def test_game_not_found(client: TestClient):
    res = client.get("/api/v1/games/nonexistent")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_candidates_pagination(client: TestClient):
    game_id = _create(client)
    res = client.get(f"/api/v1/games/{game_id}/candidates?limit=10&offset=5")
    body = res.json()
    assert body["total"] == 2315
    assert len(body["words"]) == 10


def test_answer_never_leaks(client: TestClient):
    game_id = _create(client)
    answer = _answer(client, game_id)
    client.post(f"/api/v1/games/{game_id}/guesses", json={"word": "crane"})
    res = client.get(f"/api/v1/games/{game_id}")
    # the answer must not appear anywhere in the serialized state
    assert f'"{answer}"' not in res.text or answer == "crane"
    assert "answer" not in res.json()


def test_quantum_run_snapshots(client: TestClient):
    game_id = _create(client)
    # narrow the candidate set first
    client.post(f"/api/v1/games/{game_id}/guesses", json={"word": "crane"})
    res = client.post(f"/api/v1/games/{game_id}/quantum/run", json={"iterations": 3})
    assert res.status_code == 200
    body = res.json()
    assert body["n_qubits"] == 12
    assert body["n_states"] == 4096
    assert body["candidate_count"] >= 1
    assert len(body["snapshots"]) == 4  # iteration 0..3

    snap0 = body["snapshots"][0]
    # initial uniform superposition over ALL 4096 states
    assert snap0["top"][0]["probability"] == pytest.approx(1 / 4096, rel=1e-6)
    m = body["candidate_count"]
    assert snap0["candidate_probability"] == pytest.approx(m / 4096, rel=1e-6)

    # amplification grows towards the optimum (3 < optimal here)
    probs = [s["candidate_probability"] for s in body["snapshots"]]
    assert probs == sorted(probs)
    assert len(snap0["top"]) <= 20


def test_quantum_run_validation(client: TestClient):
    game_id = _create(client)
    res = client.post(f"/api/v1/games/{game_id}/quantum/run", json={"iterations": 999})
    assert res.status_code == 422
    res = client.post(f"/api/v1/games/{game_id}/quantum/run", json={"iterations": -1})
    assert res.status_code == 422


def test_quantum_run_top_words_are_candidates(client: TestClient):
    game_id = _create(client)
    answer = _answer(client, game_id)
    client.post(f"/api/v1/games/{game_id}/guesses", json={"word": answer})
    # candidate set is now exactly {answer}
    res = client.post(f"/api/v1/games/{game_id}/quantum/run", json={"iterations": 50})
    body = res.json()
    assert body["candidate_count"] == 1
    assert body["optimal_iterations"] == 50
    final = body["snapshots"][-1]
    assert final["top"][0]["word"] == answer
    assert final["top"][0]["probability"] > 0.999


def test_quantum_measure(client: TestClient):
    game_id = _create(client)
    answer = _answer(client, game_id)
    client.post(f"/api/v1/games/{game_id}/guesses", json={"word": answer})
    # M=1: at the optimum nearly every shot lands on the answer
    res = client.post(
        f"/api/v1/games/{game_id}/quantum/measure",
        json={"iterations": 50, "shots": 20},
    )
    assert res.status_code == 200
    body = res.json()
    top = body["results"][0]
    assert top["word"] == answer
    assert top["is_candidate"] is True
    assert top["count"] >= 19
    assert sum(r["count"] for r in body["results"]) == 20


def test_quantum_measure_validation(client: TestClient):
    game_id = _create(client)
    res = client.post(
        f"/api/v1/games/{game_id}/quantum/measure",
        json={"iterations": 1, "shots": 0},
    )
    assert res.status_code == 422


def test_quantum_circuit_svg(client: TestClient):
    game_id = _create(client)
    res = client.get(f"/api/v1/games/{game_id}/quantum/circuit?iterations=8")
    assert res.status_code == 200
    body = res.json()
    assert body["iterations"] == 8
    assert body["drawn_iterations"] == 3  # capped for readability
    assert body["svg"].lstrip().startswith("<?xml") or "<svg" in body["svg"]
    assert "Oracle" in body["svg"]
    assert "Diffusion" in body["svg"]


def test_quantum_circuit_zero_iterations(client: TestClient):
    game_id = _create(client)
    res = client.get(f"/api/v1/games/{game_id}/quantum/circuit?iterations=0")
    body = res.json()
    assert body["drawn_iterations"] == 0
    assert "Oracle" not in body["svg"]  # only the H column
