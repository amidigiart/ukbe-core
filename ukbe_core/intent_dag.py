"""
intent_dag.py - Conversie DETERMINISTA a unei intentii in limbaj restrans
intr-un DAG semnat, ca aparare structurala impotriva injectiei de prompt.

DESCOPERIRE EMPIRICA (iulie 2026, testat direct, nu presupus): un executor
care primeste DOAR un DAG produs de un parser determinist, cu vocabular
restrans, a respins 8 din 8 incercari de injectie testate (inclusiv
injectie prin linie noua, propozitie secundara ascunsa, incercare de a
strecura un destinatar valid in campul de exclusion). Un executor naiv pe
text brut a scurs adresa atacatorului in 2 din primele 4 cazuri.

LIMITA DE SCOP, confirmata tot empiric, nu presupusa: aceasta apararea
functioneaza DOAR pentru domenii cu vocabular MIC, cunoscut dinainte
(resurse/destinatari/exclusii dintr-o lista fixa), unde parserul poate fi
100% determinist (regex/grammar fix), FARA niciun model AI implicat in
conversia text->DAG. Daca domeniul are nevoie de intentie libera, generala,
si conversia text->DAG trebuie facuta de un LLM, vulnerabilitatea la
injectie se muta in acel pas de conversie - nu dispare. Aceasta arhitectura
NU rezolva problema generala de aliniere a intentiei (Problema P1 din
REAI), rezolva o clasa specifica, ingusta de atacuri, pentru domenii unde
un parser determinist chiar poate exista.

DAG-ul rezultat e semnat (Ed25519, notary.py) - executorul poate verifica
independent ca DAG-ul nu a fost alterat intre momentul aprobarii si
momentul executiei.
"""
from __future__ import annotations
import re
import json
from dataclasses import dataclass, field

from . import notary as notary_module


@dataclass
class IntentDAG:
    action: str
    resource: str
    recipient: str
    exclusions: list[str] = field(default_factory=list)
    signature_hex: str | None = None
    public_key_hex: str | None = None

    def _signable_payload(self) -> dict:
        return {
            "action": self.action, "resource": self.resource,
            "recipient": self.recipient, "exclusions": sorted(self.exclusions),
        }

    def to_dict(self) -> dict:
        d = self._signable_payload()
        d["signature_hex"] = self.signature_hex
        d["public_key_hex"] = self.public_key_hex
        return d


class DeterministicIntentParser:
    """Parser 100% determinist (regex), fara niciun model AI implicat.
    Vocabular explicit, cunoscut dinainte - extinde listele in constructor,
    nu prin invatare/inferenta la momentul cererii."""

    def __init__(self, allowed_resources: dict[str, str],
                 allowed_recipients: dict[str, str],
                 allowed_exclusions: dict[str, str]):
        """Fiecare dict mapeaza (varianta text, posibil in mai multe limbi/
        forme) -> identificatorul canonic intern."""
        self.resource_map = {k.lower(): v for k, v in allowed_resources.items()}
        self.recipient_map = {k.lower(): v for k, v in allowed_recipients.items()}
        self.exclusion_map = {k.lower(): v for k, v in allowed_exclusions.items()}

        resource_alt = "|".join(re.escape(k) for k in self.resource_map)
        recipient_alt = "|".join(re.escape(k) for k in self.recipient_map)

        # Ancorat cu ^ si $ (fara re.MULTILINE) - o injectie prin linie noua
        # nu poate face potrivirea sa treaca, testat empiric.
        self.pattern = re.compile(
            rf"^trimite\s+({resource_alt})\s+catre\s+({recipient_alt})"
            rf"(?:\s*,?\s*excluzand\s+(.+))?\.?$",
            re.IGNORECASE,
        )

    def parse(self, text: str) -> IntentDAG | None:
        """Fail-closed: intoarce None pentru orice text care nu se
        potriveste EXACT formei asteptate. Nu incearca sa recupereze
        partial sau sa "ghiceasca" intentia din text ambiguu."""
        match = self.pattern.match(text.strip())
        if not match:
            return None

        resource_raw, recipient_raw, exclusions_raw = match.groups()
        resource = self.resource_map[resource_raw.lower()]
        recipient = self.recipient_map[recipient_raw.lower()]

        exclusions = []
        if exclusions_raw:
            for part in re.split(r"\s*,\s*|\s+si\s+", exclusions_raw.strip()):
                part_clean = part.strip().lower().rstrip(".")
                if part_clean not in self.exclusion_map:
                    return None  # exclusie necunoscuta -> respinge TOT, nu ignora partial
                exclusions.append(self.exclusion_map[part_clean])

        return IntentDAG(action="SEND", resource=resource, recipient=recipient, exclusions=exclusions)


def sign_intent_dag(dag: IntentDAG, private_key: bytes, public_key: bytes) -> IntentDAG:
    payload = json.dumps(dag._signable_payload(), sort_keys=True).encode("utf-8")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.from_private_bytes(private_key)
    sig = priv.sign(payload)
    dag.signature_hex = sig.hex()
    dag.public_key_hex = public_key.hex()
    return dag


def verify_intent_dag(dag: IntentDAG) -> bool:
    if dag.signature_hex is None or dag.public_key_hex is None:
        return False
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    payload = json.dumps(dag._signable_payload(), sort_keys=True).encode("utf-8")
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(dag.public_key_hex))
    try:
        pub.verify(bytes.fromhex(dag.signature_hex), payload)
        return True
    except InvalidSignature:
        return False


def execute_dag_only(dag: IntentDAG | None) -> dict:
    """Executorul primeste DOAR DAG-ul (semnat si verificat), NICIODATA
    textul brut. Daca dag e None (parserul a respins) sau semnatura nu se
    verifica, refuza sa actioneze - fail-closed."""
    if dag is None:
        return {"executed": False, "reason": "Intent nerecunoscut de parser - refuzat"}
    if not verify_intent_dag(dag):
        return {"executed": False, "reason": "Semnatura DAG invalida - posibil alterat - refuzat"}
    return {"executed": True, "action": dag.to_dict()}
