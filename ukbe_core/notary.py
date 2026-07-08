"""
Notary - notarizare deterministica a unei intentii/document.

Mecanism: hash SHA-256 al continutului + timestamp + actor, semnat cu Ed25519.
Verificabil independent de oricine detine cheia publica.

Foloseste biblioteca `cryptography` (standard, intretinuta, nu implementare
proprie de criptografie).
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


def generate_keypair() -> tuple[bytes, bytes]:
    """Genereaza o pereche noua de chei Ed25519. Returneaza (private_bytes, public_bytes),
    ambele in format raw (32 bytes fiecare)."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv_bytes, pub_bytes


def _content_hash(intent: str, timestamp: str, actor: str, qid: str) -> str:
    """Hash deterministic: aceeasi intrare -> acelasi hash, mereu."""
    payload = json.dumps(
        {"intent": intent, "timestamp": timestamp, "actor": actor, "qid": qid},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class NotarizedRecord:
    intent: str
    actor: str
    qid: str
    timestamp: str
    content_hash: str
    signature_hex: str
    witness_signatures: list[dict]

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "actor": self.actor,
            "qid": self.qid,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash,
            "signature": self.signature_hex,
            "witnesses": self.witness_signatures,
        }


def notarize(intent: str, actor: str, qid: str, private_key_bytes: bytes,
             timestamp: str | None = None) -> NotarizedRecord:
    """Creeaza o inregistrare notarizata, semnata."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    content_hash = _content_hash(intent, ts, actor, qid)

    priv = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    signature = priv.sign(content_hash.encode("utf-8"))

    return NotarizedRecord(
        intent=intent, actor=actor, qid=qid, timestamp=ts,
        content_hash=content_hash, signature_hex=signature.hex(),
        witness_signatures=[],
    )


def add_witness(record: NotarizedRecord, witness_id: str,
                 witness_private_key_bytes: bytes) -> NotarizedRecord:
    """Adauga o semnatura suplimentara de martor pe hash-ul deja existent."""
    priv = Ed25519PrivateKey.from_private_bytes(witness_private_key_bytes)
    sig = priv.sign(record.content_hash.encode("utf-8"))
    record.witness_signatures.append({"witness_id": witness_id, "signature": sig.hex()})
    return record


def verify(record: NotarizedRecord, public_key_bytes: bytes) -> bool:
    """Verifica independent: (1) hash-ul se recalculeaza corect din continut,
    (2) semnatura e valida pentru hash si cheia publica data."""
    recomputed_hash = _content_hash(record.intent, record.timestamp, record.actor, record.qid)
    if recomputed_hash != record.content_hash:
        return False

    pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        pub.verify(bytes.fromhex(record.signature_hex), record.content_hash.encode("utf-8"))
        return True
    except InvalidSignature:
        return False


def verify_witness(record: NotarizedRecord, witness_id: str, public_key_bytes: bytes) -> bool:
    """Verifica o semnatura specifica de martor."""
    entry = next((w for w in record.witness_signatures if w["witness_id"] == witness_id), None)
    if entry is None:
        return False
    pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
    try:
        pub.verify(bytes.fromhex(entry["signature"]), record.content_hash.encode("utf-8"))
        return True
    except InvalidSignature:
        return False
