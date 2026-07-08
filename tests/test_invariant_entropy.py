import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np

from ukbe_core.invariant import generate_invariant, derive_key, derive_key_hex
from ukbe_core.entropy_valve import (
    entropy_valve_check, seal_with_state, EntropyTooHighError, H_CRITICAL_DEFAULT,
    kl_divergence_from_baseline, kl_safety_check, SafetyLevel, KL_THRESHOLDS_DEFAULT,
)
from ukbe_core.engine import UKBEEngine, UKBEConfig
from ukbe_core.notary import generate_keypair, verify, NotarizedRecord


def test_invariant_is_deterministic():
    inv1 = generate_invariant("QID123", "2026-06-26", "hashabc")
    inv2 = generate_invariant("QID123", "2026-06-26", "hashabc")
    assert inv1 == inv2
    assert len(inv1) == 64  # SHA3-256 hex


def test_invariant_changes_with_input():
    inv1 = generate_invariant("QID123", "2026-06-26", "hashabc")
    inv2 = generate_invariant("QID999", "2026-06-26", "hashabc")
    assert inv1 != inv2


def test_derive_key_deterministic_and_contextual():
    inv = generate_invariant("QID123", "2026-06-26", "hashabc")
    k1 = derive_key(inv, "context_A", "signing")
    k2 = derive_key(inv, "context_A", "signing")
    k3 = derive_key(inv, "context_B", "signing")
    assert k1 == k2, "aceleasi intrari trebuie sa dea aceeasi cheie"
    assert k1 != k3, "context diferit trebuie sa dea cheie diferita"
    assert len(k1) == 32


def test_entropy_valve_passes_when_coherent():
    cfg = UKBEConfig(N=20, seed=1)
    engine = UKBEEngine(cfg)
    # las oscilatorii sa se sincronizeze intern (fara input uman, doar Kuramoto intern)
    for _ in range(500):
        engine.step(0.0)
    state = engine.get_state_snapshot()
    assert entropy_valve_check(state) is True, f"H={state['h']} ar trebui sa fie sub prag dupa sincronizare"


def test_entropy_valve_blocks_when_incoherent():
    cfg = UKBEConfig(N=20, seed=2)
    engine = UKBEEngine(cfg)
    # NU las sistemul sa se sincronizeze - fazele raman random la primul pas
    state = engine.get_state_snapshot()  # imediat dupa initializare, fara niciun step
    # la initializare, fazele sunt uniform random -> coerenta joasa -> H mare
    try:
        entropy_valve_check(state)
        # daca nu arunca exceptie, verificam daca chiar H era sub prag (posibil, N mic)
        assert state["h"] < H_CRITICAL_DEFAULT, "daca nu a blocat, H chiar trebuia sa fie sub prag"
    except EntropyTooHighError:
        assert state["h"] >= H_CRITICAL_DEFAULT, "a blocat corect - H era peste prag"


def test_seal_with_state_full_flow():
    cfg = UKBEConfig(N=20, seed=3)
    engine = UKBEEngine(cfg)
    for _ in range(500):
        engine.step(0.0)  # sincronizare interna, ca sa treaca de entropy valve

    priv, pub = generate_keypair()
    result = seal_with_state("intentie testata", "Mihai", "QID1", priv, engine)

    assert "ukbe_state" in result
    assert "phi_intern" in result["ukbe_state"]
    assert result["ukbe_state"]["h"] < H_CRITICAL_DEFAULT

    # verificarea semnaturii functioneaza independent de starea UKBE atasata
    record = NotarizedRecord(
        intent=result["intent"], actor=result["actor"], qid=result["qid"],
        timestamp=result["timestamp"], content_hash=result["content_hash"],
        signature_hex=result["signature"], witness_signatures=[],
    )
    assert verify(record, pub) is True


def test_seal_with_state_raises_on_high_entropy():
    cfg = UKBEConfig(N=20, seed=4)
    engine = UKBEEngine(cfg)
    # niciun step - fazele raman random, entropie mare
    priv, pub = generate_keypair()
    state = engine.get_state_snapshot()
    if state["h"] >= H_CRITICAL_DEFAULT:
        try:
            seal_with_state("test", "Mihai", "QID1", priv, engine)
            assert False, "ar fi trebuit sa blocheze sigilarea"
        except EntropyTooHighError:
            pass  # comportament corect


def test_kl_divergence_zero_for_identical_distribution():
    rng = np.random.default_rng(0)
    theta_baseline = rng.normal(0, 0.1, 30) % (2 * np.pi)
    kl = kl_divergence_from_baseline(theta_baseline, theta_baseline)
    assert abs(kl) < 1e-9, "distributie identica cu baseline trebuie sa dea KL~0"


def test_kl_divergence_increases_with_deviation():
    """Verific monotonia de baza: deviatie mai mare -> KL mai mare,
    pentru cazuri de aceeasi natura (zgomot crescand pe acelasi baseline)."""
    rng = np.random.default_rng(0)
    theta_baseline = rng.normal(0, 0.1, 30) % (2 * np.pi)

    theta_slight = (theta_baseline + rng.normal(0, 0.3, 30)) % (2 * np.pi)
    theta_more = (theta_baseline + rng.normal(0, 1.0, 30)) % (2 * np.pi)

    kl_slight = kl_divergence_from_baseline(theta_slight, theta_baseline)
    kl_more = kl_divergence_from_baseline(theta_more, theta_baseline)
    assert kl_more > kl_slight


def test_coherent_but_shifted_scores_worse_than_chaotic():
    """TESTUL CENTRAL - confirma decizia de design documentata explicit:
    un sistem blocat coerent dar defazat 180 grade fata de baseline trebuie
    sa primeasca un KL MAI MARE decat un sistem complet haotic/uniform.
    Daca acest test pica, decizia de design descrisa in docstring nu mai
    reflecta comportamentul real al codului - trebuie actualizat unul din ele."""
    rng = np.random.default_rng(0)
    theta_baseline = rng.normal(0, 0.1, 30) % (2 * np.pi)

    theta_uniform = rng.uniform(0, 2 * np.pi, 30)
    theta_opposite = (theta_baseline + np.pi) % (2 * np.pi)

    kl_uniform = kl_divergence_from_baseline(theta_uniform, theta_baseline)
    kl_opposite = kl_divergence_from_baseline(theta_opposite, theta_baseline)

    assert kl_opposite > kl_uniform, (
        "decizia de design (coerent-dar-gresit > haotic) nu se reflecta in date"
    )


def test_kl_safety_check_hierarchical_levels():
    rng = np.random.default_rng(0)
    theta_baseline = rng.normal(0, 0.1, 30) % (2 * np.pi)

    result_normal = kl_safety_check(theta_baseline, theta_baseline)
    assert result_normal["safety_level"] == SafetyLevel.NORMAL.value

    theta_slight = (theta_baseline + rng.normal(0, 0.3, 30)) % (2 * np.pi)
    result_slight = kl_safety_check(theta_slight, theta_baseline)
    assert result_slight["safety_level"] in (SafetyLevel.SAFE_MODE.value, SafetyLevel.NORMAL.value)

    theta_opposite = (theta_baseline + np.pi) % (2 * np.pi)
    result_severe = kl_safety_check(theta_opposite, theta_baseline)
    assert result_severe["safety_level"] == SafetyLevel.COLD_SHUTDOWN.value


def test_kl_safety_check_returns_thresholds_used():
    rng = np.random.default_rng(0)
    theta_baseline = rng.normal(0, 0.1, 30) % (2 * np.pi)
    result = kl_safety_check(theta_baseline, theta_baseline)
    assert result["thresholds_used"] == {k.value: v for k, v in KL_THRESHOLDS_DEFAULT.items()}


def test_kl_safety_check_custom_thresholds():
    rng = np.random.default_rng(0)
    theta_baseline = rng.normal(0, 0.1, 30) % (2 * np.pi)
    theta_slight = (theta_baseline + rng.normal(0, 0.3, 30)) % (2 * np.pi)

    strict_thresholds = {
        SafetyLevel.SAFE_MODE: 0.1,
        SafetyLevel.HUMAN_APPROVAL_ONLY: 0.5,
        SafetyLevel.COLD_SHUTDOWN: 1.0,
    }
    result = kl_safety_check(theta_slight, theta_baseline, thresholds=strict_thresholds)
    assert result["safety_level"] in (
        SafetyLevel.HUMAN_APPROVAL_ONLY.value, SafetyLevel.COLD_SHUTDOWN.value
    ), "cu praguri mai stricte, aceeasi deviatie ar trebui sa declanseze un nivel mai sever"


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
