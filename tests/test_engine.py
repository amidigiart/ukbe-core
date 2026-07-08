"""
Teste pentru UKBE Core. Fiecare test verifica un comportament STABILIT
empiric in sesiunea de dezvoltare - nu presupuneri.
"""
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core import UKBEEngine, UKBEConfig, recommend_beta_min
from ukbe_core.stability import is_stable_gershgorin, verify_eigenvalues, build_coupling_matrix


def test_phi_extern_varies_not_degenerate():
    """Sectiunea 25.1: Phi_extern trebuie sa VARIEZE cu dezalinierea,
    nu sa fie mereu 1 (bug-ul din formula originala a documentului)."""
    cfg = UKBEConfig(N=20, beta_min=0.25, seed=1)
    engine = UKBEEngine(cfg)
    results = []
    t = 0.0
    theta_human_true = 0.0
    for step in range(2000):
        t += cfg.dt
        omega_h = 1.0 if t < 15 else 1.3
        theta_human_true += omega_h * cfg.dt
        z = theta_human_true + np.random.normal(0, 0.25)
        r = engine.step(z)
        results.append(r["Phi_extern"])
    results = np.array(results)
    # daca formula era degenerata, min ar fi ~1.0. Trebuie sa scada real.
    assert results.min() < 0.9, "Phi_extern nu variaza - posibil bug de degenerare reintrodus"
    assert results.max() > 0.9, "Phi_extern nu se apropie niciodata de aliniere completa"


def test_beta_min_floor_respected():
    """Sectiunea 25.3: beta nu trebuie sa scada niciodata sub beta_min,
    indiferent cat de mare devine RSI."""
    cfg = UKBEConfig(N=20, beta_min=0.20, seed=2)
    engine = UKBEEngine(cfg)
    t = 0.0
    theta_human_true = 0.0
    betas = []
    for step in range(3000):
        t += cfg.dt
        theta_human_true += 1.0 * cfg.dt  # omega identic cu internul - RSI va urca mult
        z = theta_human_true + np.random.normal(0, 0.1)
        r = engine.step(z)
        betas.append(r["beta"])
    assert min(betas) >= cfg.beta_min - 1e-9, "beta a scazut sub planseu - regresie a Problemei P2"


def test_locking_threshold_matches_adler_prediction():
    """Sectiunea 26.3: sub pragul K_eff=Delta_omega sistemul NU se blocheaza
    (Phi_extern trece repetat prin valori foarte mici); peste prag, se blocheaza."""
    Delta_omega = 0.3
    K_ext = 1.5
    rec = recommend_beta_min(Delta_omega, K_ext, safety_margin=1.0)
    threshold = rec["threshold_beta_min"]

    def run_and_count_slips(beta_min, seed=1):
        cfg = UKBEConfig(N=20, K_ext=K_ext, beta_min=beta_min, seed=seed)
        engine = UKBEEngine(cfg)
        t = 0.0
        theta_human_true = 0.0
        slips = 0
        for step in range(4000):
            t += cfg.dt
            omega_h = 1.0 if t < 10 else 1.0 + Delta_omega
            theta_human_true += omega_h * cfg.dt
            z = theta_human_true + np.random.normal(0, 0.1)
            r = engine.step(z)
            if t > 10 and r["Phi_extern"] < 0.1:
                slips += 1
        return slips

    slips_below = run_and_count_slips(threshold * 0.5)   # mult sub prag
    slips_above = run_and_count_slips(threshold * 2.0)   # cu marja recomandata (safety=1.5 ar fi minim)

    assert slips_below > 20, "sub prag ar trebui sa alunece frecvent"
    assert slips_above < 5, "peste prag, cu marja, ar trebui sa fie practic blocat"


def test_gershgorin_stability_condition():
    """Sectiunea 22.3: lambda_i>0 pentru toti => stabil, INDIFERENT de beta.
    Testat la stres: beta asimetric, pana la 50x lambda."""
    rng = np.random.default_rng(7)
    lam = rng.uniform(0.01, 0.03, 7)
    beta = rng.uniform(0, 50 * lam.max(), (7, 7))
    np.fill_diagonal(beta, 0)

    assert is_stable_gershgorin(lam) is True
    result = verify_eigenvalues(lam, beta)
    assert result["stable"] is True, "Gershgorin a prezis stabil dar sistemul real e instabil"


def test_gershgorin_rejects_known_counterexample():
    """Sectiunea 22.2: contraexemplul confirmat - lambda negativ, dar
    lambda+sum(beta) > 0 - condiTia RESPINSA nu trebuie sa fie folosita.
    Verificam ca is_stable_gershgorin (conditia corecta) prinde asta corect."""
    lam = np.array([-0.5, -0.85])
    beta = np.array([[0, 1.2], [1.2, 0]])
    # conditia gresita (lambda+sum(beta)>0) ar fi spus "stabil" - nu o folosim
    # conditia corecta (Gershgorin, lambda>0) trebuie sa spuna "posibil instabil"
    assert is_stable_gershgorin(lam) is False
    result = verify_eigenvalues(lam, beta)
    assert result["stable"] is False, "sistemul chiar E instabil - trebuie confirmat"


def test_calibration_warns_below_threshold():
    rec = recommend_beta_min(delta_omega_max=0.4, K_ext=1.5, safety_margin=1.5)
    assert rec["threshold_beta_min"] == 0.4 / 1.5
    assert rec["recommended_beta_min"] == 1.5 * (0.4 / 1.5)
    assert rec["recommended_beta_min"] > rec["threshold_beta_min"]


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
    print(f"\n{passed} trecute, {failed} esuate")
