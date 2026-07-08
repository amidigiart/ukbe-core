import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np

from ukbe_core.vector_consensus import VectorConsensusEngine, VectorConsensusConfig, normalize


def test_converges_from_uncorrelated_to_high_consensus():
    """Reproduce rezultatul testat manual: pornind din stari necorelate,
    consensul trebuie sa creasca monoton spre valori mari."""
    cfg = VectorConsensusConfig(num_modules=5, dim=64, K=1.5, dt=0.05, seed=42)
    engine = VectorConsensusEngine(cfg)

    initial_score = engine.consensus_score()
    assert initial_score < 0.3, "starile initiale ar trebui sa fie slab corelate"

    scores = []
    for _ in range(30):
        result = engine.step()
        scores.append(result["consensus_score"])

    assert scores[-1] > 0.85, f"dupa 30 de pasi, consensul ar trebui sa fie ridicat, nu {scores[-1]}"
    # monotonie aproximativa - nu stricta la fiecare pas, dar tendinta clara
    assert scores[-1] > scores[0]
    assert scores[15] > scores[0]


def test_recovers_after_large_perturbation():
    cfg = VectorConsensusConfig(num_modules=5, dim=64, K=1.5, dt=0.05, seed=42)
    engine = VectorConsensusEngine(cfg)

    for _ in range(20):
        engine.step()
    score_before = engine.consensus_score()
    assert score_before > 0.5, "ar trebui sa fi convers substantial pana la pasul 20"

    rng = np.random.default_rng(1)
    engine.states = normalize(engine.states + rng.standard_normal(engine.states.shape) * 2.0)
    score_after_perturbation = engine.consensus_score()
    assert score_after_perturbation < score_before, "perturbarea trebuie sa scada real consensul"

    for _ in range(20):
        engine.step()
    score_recovered = engine.consensus_score()
    assert score_recovered > score_after_perturbation + 0.3, "trebuie sa se recupereze substantial"


def test_identical_states_give_consensus_one():
    cfg = VectorConsensusConfig(num_modules=4, dim=32, seed=1)
    engine = VectorConsensusEngine(cfg)
    same_vector = np.ones(32)
    for i in range(4):
        engine.update_state(i, same_vector.copy())
    assert abs(engine.consensus_score() - 1.0) < 1e-9


def test_orthogonal_states_give_consensus_near_zero():
    cfg = VectorConsensusConfig(num_modules=4, dim=32, seed=1)
    engine = VectorConsensusEngine(cfg)
    q, _ = np.linalg.qr(np.random.default_rng(0).standard_normal((32, 4)))
    for i in range(4):
        engine.update_state(i, q[:, i])
    assert abs(engine.consensus_score()) < 0.05


def test_update_state_rejects_wrong_dimension():
    cfg = VectorConsensusConfig(num_modules=3, dim=16, seed=1)
    engine = VectorConsensusEngine(cfg)
    try:
        engine.update_state(0, np.ones(8))  # dimensiune gresita
        assert False, "ar fi trebuit sa respinga dimensiunea gresita"
    except ValueError:
        pass


def test_update_state_rejects_zero_vector():
    cfg = VectorConsensusConfig(num_modules=3, dim=16, seed=1)
    engine = VectorConsensusEngine(cfg)
    try:
        engine.update_state(0, np.zeros(16))
        assert False, "ar fi trebuit sa respinga vectorul nul"
    except ValueError:
        pass


def test_vectorized_step_matches_loop_based_reference():
    """Regresie: formula vectorizata trebuie sa ramana echivalenta cu
    suma directa (bucla), verificata initial la precizia masinii."""
    def lohe_step_loop(states, K, dt):
        N = states.shape[0]
        new_states = states.copy()
        for i in range(N):
            coupling = np.zeros(states.shape[1])
            for j in range(N):
                if i == j:
                    continue
                proj = states[j] - np.dot(states[i], states[j]) * states[i]
                coupling += proj
            new_states[i] = states[i] + dt * K * coupling / N
        return normalize(new_states)

    cfg = VectorConsensusConfig(num_modules=5, dim=16, K=1.5, dt=0.05, seed=7)
    engine = VectorConsensusEngine(cfg)
    states_loop = engine.states.copy()

    for _ in range(10):
        engine.step()
        states_loop = lohe_step_loop(states_loop, cfg.K, cfg.dt)

    diff = np.abs(engine.states - states_loop).max()
    assert diff < 1e-9, f"vectorizarea a deviat de la referinta cu bucla: {diff}"


def test_get_state_snapshot_structure():
    cfg = VectorConsensusConfig(num_modules=3, dim=8, seed=1)
    engine = VectorConsensusEngine(cfg)
    engine.step()
    snapshot = engine.get_state_snapshot()
    assert "consensus_score" in snapshot
    assert "states" in snapshot
    assert len(snapshot["states"]) == 3


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} trecute, {failed} esuate")
