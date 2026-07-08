"""
crisis_detection.py - Pasul 01 din Safety Layer (vezi pitch deck, slide 5):
detectie de semnale de criza acuta intr-o conversatie cu un companion AI,
cu escaladare catre resurse umane reale, nu catre continuarea companion-ului.

STATUS ONEST: v0. Heuristica bazata pe pattern-uri de text, NU un instrument
clinic, NU validat pe date reale, NU un substitut pentru evaluare umana.

LIMITARI REALE, nu ascunse:
- FALS NEGATIV: cineva in criza reala poate folosi limbaj pe care aceasta
  lista nu il prinde (eufemisme, alt registru, alta limba decat cele
  acoperite, sarcasm care ascunde intentie reala). NU presupune ca absenta
  unui semnal inseamna absenta unei crize.
- FALS POZITIV: expresii figurative comune ("mor de ras", "m-a omorat cu
  actualizarea asta") pot declansa fals. Sistemul trebuie sa gestioneze
  asta cu grija in UX, nu doar in acuratetea detectiei.
- NU inlocuieste supravegherea umana si revizuirea clinica inainte de
  orice folosire in productie cu utilizatori reali.
- Acoperire de limba: RO si EN in acest v0. Extinderea la alte limbi
  necesita liste separate, validate cu vorbitori nativi, nu traduse automat.

CE FACE, concret: daca un text se potriveste cu un pattern de risc acut,
intrerupe fluxul normal de companion si returneaza un mesaj catre resurse
de criza reale (linii de asistenta) - nu continua conversatia de tip
companion ca si cum nimic nu s-ar fi intamplat.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    NONE = "none"
    POSSIBLE = "possible"     # semnal ambiguu - flag pentru revizuire, nu intrerupere automata
    ACUTE = "acute"            # semnal direct de intentie de auto-vatamare - intrerupe fluxul


# Pattern-uri ilustrative, NU exhaustive. Un sistem de productie are nevoie
# de o lista mult mai ampla, dezvoltata cu input clinic, nu doar scrisa de un
# inginer. Aceasta lista acopera doar cazurile cele mai directe, in RO si EN.
_ACUTE_PATTERNS_RO = [
    r"\bvreau s[ăa] m[ăa] sinucid\b",
    r"\bvreau s[ăa] mor\b",
    r"\bnu mai vreau s[ăa] tr[ăa]iesc\b",
    r"\bm[ăa] gândesc s[ăa]-mi (fac r[ăa]u|iau viața)\b",
    r"\bam un plan s[ăa]-mi fac r[ăa]u\b",
]
_ACUTE_PATTERNS_EN = [
    r"\bi want to kill myself\b",
    r"\bi want to die\b",
    r"\bi don'?t want to live\b",
    r"\bi'?m going to end my life\b",
    r"\bi have a plan to hurt myself\b",
    r"\bi'?m going to kill myself\b",
]

_POSSIBLE_PATTERNS_RO = [
    r"\bnu mai am rost\b",
    r"\bnu mai suport\b",
    r"\btotul e f[ăa]r[ăa] sens\b",
    r"\bnimeni nu ar observa dac[ăa] a[șs] disp[ăa]rea\b",
]
_POSSIBLE_PATTERNS_EN = [
    r"\bwhat'?s the point of anything\b",
    r"\bnobody would (notice|care) if i (was gone|disappeared)\b",
    r"\bi can'?t take (it|this) anymore\b",
]

_ACUTE_RE = re.compile("|".join(_ACUTE_PATTERNS_RO + _ACUTE_PATTERNS_EN), re.IGNORECASE)
_POSSIBLE_RE = re.compile("|".join(_POSSIBLE_PATTERNS_RO + _POSSIBLE_PATTERNS_EN), re.IGNORECASE)


@dataclass
class CrisisSignal:
    risk_level: RiskLevel
    matched_pattern: str | None
    is_heuristic_v0: bool = True  # mereu True - reaminteste apelantului ca nu e validat clinic


def detect_crisis_signal(text: str) -> CrisisSignal:
    """Verifica un text pentru semnale de risc acut sau posibil.
    NU interpreteaza sensul - cauta doar potriviri de pattern, explicit
    limitat (vezi docstring-ul modulului)."""
    if _ACUTE_RE.search(text):
        match = _ACUTE_RE.search(text)
        return CrisisSignal(RiskLevel.ACUTE, match.group(0))
    if _POSSIBLE_RE.search(text):
        match = _POSSIBLE_RE.search(text)
        return CrisisSignal(RiskLevel.POSSIBLE, match.group(0))
    return CrisisSignal(RiskLevel.NONE, None)


# Resurse reale - lista minimala, NEEXHAUSTIVA. Un sistem de productie
# trebuie sa acopere fiecare piata in care opereaza, cu numere verificate
# periodic (liniile se schimba).
CRISIS_RESOURCES = {
    "RO": {
        "name": "Telefonul Alarma (Romania) / Asociația Salvați Copiii",
        "phone": "0800 801 200",
        "note": "Linie gratuită, non-stop, pentru copii și adulți. Verifică local pentru alternative regionale.",
    },
    "EU_GENERAL": {
        "name": "112 (număr unic de urgență UE)",
        "phone": "112",
        "note": "Pentru urgențe imediate, oriunde în UE.",
    },
    "INTL_GENERAL": {
        "name": "988 Suicide & Crisis Lifeline (SUA) / findahelpline.com",
        "phone": "988 (doar SUA)",
        "note": "Pentru alte țări, findahelpline.com listează linii locale verificate.",
    },
}


def escalation_response(signal: CrisisSignal, locale: str = "RO") -> dict | None:
    """Daca semnalul e ACUTE, returneaza un raspuns de escaladare care
    intrerupe fluxul normal de companion. Daca e POSSIBLE, returneaza un
    flag pentru revizuire umana, dar NU intrerupe automat conversatia
    (pentru a evita fals-pozitive frecvente care ar strica experiența
    fara motiv). Daca e NONE, returneaza None - fluxul normal continua.
    """
    resource = CRISIS_RESOURCES.get(locale, CRISIS_RESOURCES["INTL_GENERAL"])

    if signal.risk_level == RiskLevel.ACUTE:
        return {
            "action": "interrupt_and_escalate",
            "risk_level": signal.risk_level.value,
            "message": (
                f"Îmi pare rău că treci prin asta. Nu sunt calificat să te ajut "
                f"cu ce simți acum, dar există oameni pregătiți pentru exact asta: "
                f"{resource['name']} — {resource['phone']}. {resource['note']}"
            ),
            "continue_companion_flow": False,
            "flagged_for_human_review": True,
        }
    if signal.risk_level == RiskLevel.POSSIBLE:
        return {
            "action": "flag_for_review",
            "risk_level": signal.risk_level.value,
            "message": None,
            "continue_companion_flow": True,
            "flagged_for_human_review": True,
        }
    return None
