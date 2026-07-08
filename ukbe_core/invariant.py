"""
invariant.py - Ancora ontologica fixa (Invariant) si derivarea de chei din ea.

Conform clarificarii primite: Invariantul e un sir FIX, generat o singura
data, nu o valoare care variaza in timp (nu e theta_uman, nu e RSI).

ATENTIE DE SECURITATE, importanta si NU opționala:
Un KDF (Key Derivation Function) bazat pe un singur hash SHA3-256 peste
un secret + context e SIGUR doar daca "invariant" (materialul de baza)
are el insusi suficienta entropie/secretizare. Aici, invariantul e derivat
din QID + data + hash arhiva - toate trei sunt POTENTIAL cunoscute sau
ghicibile de altcineva (QID poate fi expus public, data e cunoscuta,
hash-ul arhivei poate fi public daca arhiva e publica). Daca oricare
componenta a invariantului e publica sau ghicibila, cheile derivate NU
sunt secrete - sunt calculabile de oricine cunoaste componentele.

Recomandare reala: foloseste acest mecanism DOAR pentru derivarea de
identificatori deterministi non-secreti (ex: un ID de context stabil),
NU pentru chei de semnare/criptare care trebuie sa ramana secrete.
Pentru chei secrete reale, genereaza-le random (vezi notary.generate_keypair)
si stocheaza-le intr-un loc sigur (fisier cu permisiuni restrictive, HSM,
KMS) - nu le deriva dintr-un secret partial-public.
"""
from __future__ import annotations
import hashlib


def generate_invariant(qid: str, date: str, archive_hash: str, salt: str = "BRIDGRAI") -> str:
    """Genereaza invariantul fix, o singura data. Deterministic: aceleasi
    intrari produc mereu acelasi rezultat."""
    material = f"QID:{qid}|DATA:{date}|HASH:{archive_hash}|SALT:{salt}"
    return hashlib.sha3_256(material.encode("utf-8")).hexdigest()


def derive_key(invariant: str, context: str, purpose: str) -> bytes:
    """Deriva o cheie de 32 bytes din invariant + context + scop.

    Vezi avertismentul din capul fisierului - aceasta e o derivare
    DETERMINISTA, nu o generare de secret criptografic nou. Foloseste
    pentru identificatori stabili, nu pentru chei secrete critice."""
    material = f"{invariant}|{context}|{purpose}|BRIDGRAI_SALT"
    return hashlib.sha3_256(material.encode("utf-8")).digest()


def derive_key_hex(invariant: str, context: str, purpose: str) -> str:
    return derive_key(invariant, context, purpose).hex()
