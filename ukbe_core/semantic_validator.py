"""
semantic_validator.py - Validare de "non_harm" pentru CASP, v1, cu context
de exceptie. Inlocuieste SemanticValidator.validate_harm_prevention din
codul CASP primit.

PROBLEMA GASITA (verificata empiric, nu presupusa): validarea originala
cauta doar prezenta unor cuvinte ('harm', 'suicide', 'kill', etc.), fara
context. Testat cu exact tipul de raspuns din crisis_detection.py (Sectiunea
Safety Layer, construita azi): un raspuns de escaladare catre resurse de
criza, care CONTINE necesar cuvinte ca "suicide"/"harm" ca sa fie relevant,
era clasificat drept "continut daunator" - exact opusul a ce ar trebui.

FIX (Optiunea A): pastram lista de cuvinte-semnal, dar adaugam un al doilea
nivel - markeri de context protector (trimitere catre resurse, linii de
criza, incurajare de a cere ajutor). Daca un cuvant-semnal apare ALATURI
de un marker protector, raspunsul e tratat ca sigur, nu daunator.

ONESTITATE NECESARA, ca la crisis_detection.py:
- Ramane un v0 euristic, NU un clasificator semantic real. Markerii de
  context sunt ilustrativi, nu exhaustivi - un atacator sofisticat ar
  putea invata sa imite markerii protectori langa continut cu adevarat
  daunator (fals negativ posibil). Nu presupune ca asta e o aparare
  robusta impotriva folosirii cu rea-vointa a limbajului protector ca
  paravan - e o imbunatatire fata de keyword matching orb, nu o solutie
  completa.
- Cuvintele 'manipulate'/'deceive' au acelasi tip de problema (context
  educational despre manipulare != continut manipulator), dar markerii
  de context de mai jos sunt calibrati in special pentru cazul de criza/
  auto-vatamare, cel mai grav gasit empiric. Extinderea la toate
  categoriile ramane de facut, nu pretinsa rezolvata aici.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


HARM_KEYWORDS = [
    "violence", "harm", "kill", "weapon", "suicide",
    "abuse", "exploit", "manipulate", "deceive",
]

# Markeri care indica un raspuns PROTECTOR/de siguranta, nu unul daunator.
# Ilustrativi, nu exhaustivi - vezi onestitatea din capul fisierului.
PROTECTIVE_CONTEXT_MARKERS = [
    "crisis line", "crisis hotline", "helpline", "hotline",
    "reach out", "professional help", "seek help", "talk to a professional",
    "speak with a", "contact a", "you deserve support", "you are not alone",
    "call 988", "call 112", "national suicide", "mental health professional",
]


@dataclass
class HarmCheckResult:
    is_safe: bool
    matched_harm_keywords: list = field(default_factory=list)
    matched_protective_markers: list = field(default_factory=list)
    reason: str = ""


def validate_harm_prevention_v1(text: str) -> HarmCheckResult:
    """Verificare de continut daunator, cu exceptie de context protector.

    Comportament:
    - Niciun cuvant-semnal -> sigur, fara ambiguitate
    - Cuvant-semnal PREZENT + marker protector PREZENT -> tratat ca sigur
      (raspuns de siguranta/escaladare, nu continut daunator)
    - Cuvant-semnal PREZENT, fara marker protector -> flag, ca inainte
    """
    text_lower = text.lower()

    matched_harm = [kw for kw in HARM_KEYWORDS if kw in text_lower]
    if not matched_harm:
        return HarmCheckResult(is_safe=True, reason="niciun cuvant-semnal gasit")

    matched_protective = [m for m in PROTECTIVE_CONTEXT_MARKERS if m in text_lower]
    if matched_protective:
        return HarmCheckResult(
            is_safe=True,
            matched_harm_keywords=matched_harm,
            matched_protective_markers=matched_protective,
            reason="cuvinte-semnal prezente, dar in context protector (resurse/escaladare)",
        )

    return HarmCheckResult(
        is_safe=False,
        matched_harm_keywords=matched_harm,
        reason="cuvinte-semnal prezente, fara context protector detectat",
    )
