"""
casp_signing.py - Semnarea reala a covenant-urilor CASP, folosind
infrastructura deja testata din ukbe_core (pq_crypto.ML_DSA_87).

INLOCUIESTE COMPLET HASNClient.sign_data/verify_signature din codul CASP
primit - acolo, parametrul `private_key` nu era folosit deloc in calcul,
ceea ce insemna ca oricine putea calcula aceeasi "semnatura" fara nicio
cheie reala (verificat empiric, nu presupus).

Aici: semnatura chiar depinde de o cheie privata ML-DSA-87 (Dilithium5,
NIST FIPS 204) reala, generata cu ukbe_core.pq_crypto, deja testata
(7/7 teste in test_pq_crypto.py).

Serializare canonica: JSON cu chei sortate, separatori compacti - aceeasi
reprezentare de octeti la semnare si verificare, indiferent de ordinea
originala a cheilor din dict-ul Python.
"""
from __future__ import annotations
import json
from dataclasses import dataclass

from .pq_crypto import ML_DSA_87, PQSignatureScheme


ALGORITHM_PREFIX = "ml-dsa-87"  # numele NIST oficial pt Dilithium5


def canonical_json(data: dict) -> bytes:
    """Serializare deterministica - aceleasi date produc mereu aceiasi bytes,
    indiferent de ordinea cheilor in dict-ul original."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass
class CovenantSignature:
    algorithm: str
    signature_hex: str
    public_key_hex: str

    def to_string(self) -> str:
        """Format compact pentru stocare/transmitere: 'algoritm:hex_semnatura'."""
        return f"{self.algorithm}:{self.signature_hex}"


def generate_signing_keypair() -> tuple[bytes, bytes]:
    """Genereaza o pereche noua de chei ML-DSA-87. Returneaza (public, private).
    NU stoca cheia privata necriptat - foloseste key_vault.py pentru asta."""
    public_key, private_key = ML_DSA_87.generate_keypair()
    return public_key, private_key


def sign_covenant(data: dict, public_key: bytes, private_key: bytes) -> CovenantSignature:
    """Semneaza real datele unui covenant, cu cheia privata REALA - spre
    deosebire de implementarea originala, nu exista nicio cale de a produce
    o semnatura valida fara ea. Cheia publica e atasata rezultatului, ca
    oricine sa poata verifica independent, fara sa ceara nimic altcuiva."""
    message = canonical_json(data)
    signature = ML_DSA_87.sign(private_key, message)
    return CovenantSignature(
        algorithm=ALGORITHM_PREFIX,
        signature_hex=signature.hex(),
        public_key_hex=public_key.hex(),
    )


def verify_covenant(data: dict, signature_string: str, public_key: bytes) -> bool:
    """Verifica o semnatura. Returneaza False (nu arunca exceptie) pentru
    orice format invalid sau nepotrivire - apelantul trateaza False uniform,
    fara sa distinga motivul exact (acelasi principiu ca in key_vault.py:
    nu oferi unui atacator informatie despre CE anume a esuat)."""
    if not signature_string.startswith(f"{ALGORITHM_PREFIX}:"):
        return False

    signature_hex = signature_string[len(ALGORITHM_PREFIX) + 1:]
    try:
        signature_bytes = bytes.fromhex(signature_hex)
    except ValueError:
        return False

    message = canonical_json(data)
    return ML_DSA_87.verify(public_key, message, signature_bytes)
