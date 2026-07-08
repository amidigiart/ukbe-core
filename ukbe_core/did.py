"""
did.py - Identificatori W3C DID (Decentralized Identifiers), metoda `did:key`.

Implementeaza metoda did:key (cea mai simpla si mai raspandita metoda DID),
conform specificatiei W3C DID Core 1.0 si did:key spec.
https://www.w3.org/TR/did-core/
https://w3c-ccg.github.io/did-method-key/

Un DID did:key e generat direct dintr-o cheie publica - nu necesita
registru, blockchain, sau server. E cel mai simplu mod REAL de a avea
identificatori DID conformi cu specificatia, fara infrastructura suplimentara.

Suporta chei Ed25519 (multicodec 0xed01) - cea mai comuna varianta.
"""
from __future__ import annotations
import base58


_MULTICODEC_ED25519_PUB = bytes([0xed, 0x01])  # prefix multicodec pentru Ed25519 public key


def public_key_to_did_key(public_key_bytes: bytes) -> str:
    """Converteste o cheie publica Ed25519 (32 bytes) intr-un DID did:key,
    conform specificatiei W3C did:key."""
    if len(public_key_bytes) != 32:
        raise ValueError("Cheia publica Ed25519 trebuie sa aiba exact 32 bytes")
    prefixed = _MULTICODEC_ED25519_PUB + public_key_bytes
    encoded = base58.b58encode(prefixed).decode("ascii")
    return f"did:key:z{encoded}"


def did_key_to_public_key(did: str) -> bytes:
    """Extrage cheia publica Ed25519 dintr-un DID did:key."""
    if not did.startswith("did:key:z"):
        raise ValueError("Nu e un did:key valid (trebuie sa inceapa cu 'did:key:z')")
    encoded = did[len("did:key:z"):]
    decoded = base58.b58decode(encoded)
    prefix, pub = decoded[:2], decoded[2:]
    if prefix != _MULTICODEC_ED25519_PUB:
        raise ValueError("Prefix multicodec necunoscut - doar Ed25519 suportat in acest modul")
    if len(pub) != 32:
        raise ValueError("Lungime neasteptata pentru cheia publica extrasa")
    return pub


def did_document(did: str) -> dict:
    """Construieste un DID Document minimal, conform structurii W3C DID Core."""
    pub = did_key_to_public_key(did)
    key_id = f"{did}#{did.split(':')[-1]}"
    return {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": did,
        "verificationMethod": [{
            "id": key_id,
            "type": "Ed25519VerificationKey2020",
            "controller": did,
            "publicKeyMultibase": did.split(":")[-1],
        }],
        "authentication": [key_id],
        "assertionMethod": [key_id],
    }
