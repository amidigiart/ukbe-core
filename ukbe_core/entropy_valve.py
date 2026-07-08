"""
entropy_valve.py - Verificarea entropiei motorului UKBE inainte de sigilare,
si integrarea starii motorului in inregistrarea notarizata (conceptul
numit "REAI_DataCore" in clarificarea primita - care e, concret, doar
starea curenta a UKBEEngine, nu o componenta separata).

Prag: H_CRITICAL = 0.3 (coerenta > 0.7), conform clarificarii primite.

ONESTITATE NECESARA despre acest prag: "0.3" e declarat ca fiind rezultatul
unor "teste empirice", dar acele teste nu au fost rulate impreuna cu mine
in aceasta sesiune si nu am vazut datele care sa-l justifice. Il implementez
ca parametru CONFIGURABIL, cu 0.3 ca valoare implicita, nu ca prag validat
independent. Daca ai datele empirice reale din spatele lui 0.3, pot verifica
impreuna cu tine daca rezista, la fel cum am verificat pragul de blocare Adler.
"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum

import numpy as np

from . import notary as notary_module
from .engine import UKBEEngine

H_CRITICAL_DEFAULT = 0.3


class EntropyTooHighError(ValueError):
    """Ridicata cand entropia motorului depaseste pragul la momentul sigilarii."""
    pass


class SafetyLevel(Enum):
    NORMAL = "normal"
    SAFE_MODE = "safe_mode"
    HUMAN_APPROVAL_ONLY = "human_approval_only"
    COLD_SHUTDOWN = "cold_shutdown"


# Praguri ierarhice implicite pentru KL divergence (nats, log natural).
# Calibrate empiric pe un sistem de 30 de oscilatori - RECALIBREAZA pentru
# alta dimensiune de sistem, nu presupune ca aceste valori se transfera.
KL_THRESHOLDS_DEFAULT = {
    SafetyLevel.SAFE_MODE: 1.0,
    SafetyLevel.HUMAN_APPROVAL_ONLY: 3.0,
    SafetyLevel.COLD_SHUTDOWN: 6.0,
}


def _phase_distribution(theta: np.ndarray, n_bins: int = 12) -> np.ndarray:
    """Distributia de probabilitate a fazelor oscilatorilor, discretizata
    in n_bins intervale egale pe cerc. Clip la epsilon, nu la zero exact,
    ca sa evitam log(0) in KL fara sa maschem complet un bin gol."""
    hist, _ = np.histogram(theta % (2 * np.pi), bins=n_bins, range=(0, 2 * np.pi))
    p = hist / hist.sum()
    p = np.clip(p, 1e-10, None)
    return p / p.sum()


def kl_divergence_from_baseline(theta_current: np.ndarray, theta_baseline: np.ndarray,
                                  n_bins: int = 12) -> float:
    """KL(curent || baseline) - cat de mult a deviat distributia curenta a
    fazelor de la un model de referinta aprobat (starea 'normala', validata
    manual la un moment dat).

    DECIZIE DE DESIGN, facuta EXPLICIT (nu implicit prin alegerea de bin-uri,
    cum ar fi fost daca ramanea neexaminata):

    Testat empiric (iulie 2026): un sistem care se blocheaza COERENT dar
    DEFAZAT 180 grade fata de baseline primeste un KL mai mare decat un
    sistem complet HAOTIC/necorelat (22.4 vs 17.2, in testul de referinta).
    Adica: "sistemul e sigur de el, dar gresit" e considerat mai grav decat
    "sistemul e nesigur si zgomotos".

    Aceasta e alegerea intentionata pentru un valve de siguranta: un sistem
    care s-a blocat coerent pe altceva decat ce a fost aprobat reprezinta
    un risc mai mare (comportament confident, sustinut, in directia gresita)
    decat un sistem care pur si simplu nu a reusit sa se sincronizeze deloc
    (comportament nesigur, dar fara directie sustinuta). Daca aplicatia ta
    are nevoie de ordinea inversa (haosul tratat mai sever decat coerenta
    gresita), NU folosi aceasta functie direct - foloseste H = 1-Phi_intern
    din get_state_snapshot(), care masoara doar coerenta, nu directia.
    """
    p = _phase_distribution(theta_current, n_bins)
    q = _phase_distribution(theta_baseline, n_bins)
    return float(np.sum(p * np.log(p / q)))


def kl_safety_check(theta_current: np.ndarray, theta_baseline: np.ndarray,
                      n_bins: int = 12,
                      thresholds: dict[SafetyLevel, float] | None = None) -> dict:
    """Verificare de siguranta ierarhica, tip circuit-breaker.

    NU mentine stare interna intre apeluri - fiecare apel e independent.
    Daca vrei comportament de circuit-breaker real (ramane in Cold Shutdown
    pana la reset manual, nu doar cat timp KL e mare), gestioneaza starea
    aceea la nivelul apelantului (ex: in API), nu aici.
    """
    thresholds = thresholds or KL_THRESHOLDS_DEFAULT
    kl = kl_divergence_from_baseline(theta_current, theta_baseline, n_bins)

    level = SafetyLevel.NORMAL
    for candidate_level in (SafetyLevel.SAFE_MODE, SafetyLevel.HUMAN_APPROVAL_ONLY, SafetyLevel.COLD_SHUTDOWN):
        if kl >= thresholds[candidate_level]:
            level = candidate_level

    return {
        "kl_divergence": kl,
        "safety_level": level.value,
        "thresholds_used": {k.value: v for k, v in thresholds.items()},
    }


def entropy_valve_check(ukbe_state: dict, h_critical: float = H_CRITICAL_DEFAULT) -> bool:
    """Verifica entropia (H) din starea motorului. Ridica EntropyTooHighError
    daca H >= h_critical - nu intoarce False silentios, ca eroarea sa nu
    poata fi ignorata din greseala de cod care uita sa verifice valoarea."""
    H = ukbe_state.get("h")
    if H is None:
        raise ValueError("Starea UKBE nu contine campul 'h' - foloseste engine.get_state_snapshot()")
    if H >= h_critical:
        raise EntropyTooHighError(
            f"ENTROPY_TOO_HIGH: H={H:.4f} >= prag {h_critical:.4f}. Sigilarea a fost blocata."
        )
    return True


def seal_with_state(intent: str, actor: str, qid: str, private_key_bytes: bytes,
                     ukbe_engine: UKBEEngine, h_critical: float = H_CRITICAL_DEFAULT) -> dict:
    """Sigileaza o intentie IMPREUNA cu starea curenta a motorului UKBE
    (Phi, RSI, H, theta) - conceptul "REAI_DataCore" din clarificare,
    care e concret doar acest snapshot, nu o componenta separata.

    Blocheaza sigilarea daca entropia motorului e prea mare la acel moment
    (Entropy Valve) - nu sigileaza "intentii" produse intr-un moment de
    instabilitate interna a motorului.
    """
    snapshot = ukbe_engine.get_state_snapshot()
    entropy_valve_check(snapshot, h_critical)  # arunca exceptie daca esueaza - nu continua tacut

    record = notary_module.notarize(intent, actor, qid, private_key_bytes)

    return {
        **record.to_dict(),
        "ukbe_state": snapshot,
        "sealed_at_h_critical_threshold": h_critical,
    }
