"""
pq_crypto.py - Primitive criptografice moderne, REALE si TESTATE:
  - Hash: SHA3-256, BLAKE3 (alternative la SHA-256 clasic)
  - Semnaturi post-cuantice: ML-DSA (Dilithium, standardizat NIST FIPS 204)
  - Schimb de chei post-cuantic: ML-KEM-1024 (Kyber1024, standardizat NIST FIPS 203)
  - Semnaturi alternative: SPHINCS+ (NIST FIPS 205, bazat doar pe hash-uri,
    considerat cea mai conservatoare optiune post-cuantica)

Toate testate direct in acest mediu, cu chei generate real si verificare
reala (nu doar import - vezi tests/test_pq_crypto.py).

DE CE ambele scheme clasice (Ed25519, in notary.py) SI post-cuantice aici:
migrarea la criptografie post-cuantica se face prin AGILITATE CRIPTOGRAFICA
(suport pentru mai multe scheme simultan, comutabile), nu printr-un
"switch" brusc. Aceasta e recomandarea NIST si ENISA pentru tranzitie -
nu inventata aici.

CE NU e inclus, si de ce:
  - Kyber/ML-KEM e un mecanism de SCHIMB DE CHEI (KEM), nu de semnare.
    Nu inlocuieste Ed25519/Dilithium pentru notarizare - e pentru
    criptare/comunicare securizata, o nevoie diferita.
  - "Comutarea la internetul cuantic" NU e inclusa - vezi QUANTUM_READINESS.md.
    Internetul cuantic (QKD, retele de entanglement) e infrastructura FIZICA,
    nu un parametru de configurare software. Ce se poate face acum e
    "crypto-agility" - codul de mai jos.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field

import blake3 as _blake3_lib
from pqcrypto.sign.ml_dsa_87 import (
    generate_keypair as _mldsa_keypair, sign as _mldsa_sign, verify as _mldsa_verify,
)
from pqcrypto.sign.sphincs_sha2_256s_simple import (
    generate_keypair as _sphincs_keypair, sign as _sphincs_sign, verify as _sphincs_verify,
)
from pqcrypto.kem.ml_kem_1024 import (
    generate_keypair as _mlkem_keypair, encrypt as _mlkem_encrypt, decrypt as _mlkem_decrypt,
)


# ---------- Hash-uri ----------

def sha3_256(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def blake3_hash(data: bytes) -> str:
    return _blake3_lib.blake3(data).hexdigest()


# ---------- Semnaturi post-cuantice ----------

@dataclass
class PQSignatureScheme:
    """Interfata unificata - permite comutare intre scheme fara sa
    schimbi codul care le foloseste (agilitate criptografica)."""
    name: str
    keypair_fn: callable
    sign_fn: callable
    verify_fn: callable

    def generate_keypair(self):
        pub, priv = self.keypair_fn()
        return pub, priv

    def sign(self, private_key: bytes, message: bytes) -> bytes:
        return self.sign_fn(private_key, message)

    def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        try:
            return bool(self.verify_fn(public_key, message, signature))
        except Exception:
            return False


ML_DSA_87 = PQSignatureScheme("ML-DSA-87 (Dilithium5, NIST FIPS 204)",
                               _mldsa_keypair, _mldsa_sign, _mldsa_verify)
SPHINCS_PLUS = PQSignatureScheme("SPHINCS+-SHA2-256s (NIST FIPS 205)",
                                  _sphincs_keypair, _sphincs_sign, _sphincs_verify)


# ---------- Schimb de chei post-cuantic (ML-KEM-1024 / Kyber1024) ----------

def kem_generate_keypair():
    """Genereaza o pereche de chei pentru schimb de chei ML-KEM-1024."""
    pub, priv = _mlkem_keypair()
    return pub, priv


def kem_encapsulate(public_key: bytes) -> tuple[bytes, bytes]:
    """Partea care initiaza: genereaza un secret comun + ciphertext-ul de trimis."""
    ciphertext, shared_secret = _mlkem_encrypt(public_key)
    return ciphertext, shared_secret


def kem_decapsulate(private_key: bytes, ciphertext: bytes) -> bytes:
    """Partea care primeste: recupereaza acelasi secret comun din ciphertext."""
    return _mlkem_decrypt(private_key, ciphertext)


# ---------- Notarizare cu agilitate criptografica (clasic + post-cuantic) ----------

@dataclass
class HybridNotarizedRecord:
    """Inregistrare notarizata cu DOUA semnaturi: una clasica (Ed25519,
    rapida, dimensiune mica) si una post-cuantica (ML-DSA sau SPHINCS+).
    Ambele trebuie sa verifice pentru ca inregistrarea sa fie valida -
    asta e agilitatea criptografica in practica, nu doar teorie."""
    content_hash_sha3: str
    content_hash_blake3: str
    classical_signature_hex: str
    pq_scheme_name: str
    pq_signature_hex: str


def hybrid_notarize(content: bytes, classical_private_key,
                     pq_scheme: PQSignatureScheme, pq_private_key: bytes) -> HybridNotarizedRecord:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    hash_sha3 = sha3_256(content)
    hash_blake3 = blake3_hash(content)

    classical_sig = classical_private_key.sign(hash_sha3.encode("utf-8"))
    pq_sig = pq_scheme.sign(pq_private_key, hash_sha3.encode("utf-8"))

    return HybridNotarizedRecord(
        content_hash_sha3=hash_sha3,
        content_hash_blake3=hash_blake3,
        classical_signature_hex=classical_sig.hex(),
        pq_scheme_name=pq_scheme.name,
        pq_signature_hex=pq_sig.hex(),
    )


def hybrid_verify(record: HybridNotarizedRecord, content: bytes,
                   classical_public_key, pq_scheme: PQSignatureScheme, pq_public_key: bytes) -> dict:
    """Verifica AMBELE semnaturi independent. Returneaza detaliu, nu doar
    True/False - ca sa se stie exact ce a esuat, daca esueaza ceva."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature

    hash_ok = (sha3_256(content) == record.content_hash_sha3 and
               blake3_hash(content) == record.content_hash_blake3)

    classical_ok = False
    try:
        classical_public_key.verify(bytes.fromhex(record.classical_signature_hex),
                                     record.content_hash_sha3.encode("utf-8"))
        classical_ok = True
    except InvalidSignature:
        classical_ok = False

    pq_ok = pq_scheme.verify(pq_public_key, record.content_hash_sha3.encode("utf-8"),
                              bytes.fromhex(record.pq_signature_hex))

    return {
        "hash_intact": hash_ok,
        "classical_signature_valid": classical_ok,
        "pq_signature_valid": pq_ok,
        "overall_valid": hash_ok and classical_ok and pq_ok,
    }
