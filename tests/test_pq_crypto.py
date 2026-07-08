import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ukbe_core.pq_crypto import (
    sha3_256, blake3_hash, ML_DSA_87, SPHINCS_PLUS,
    kem_generate_keypair, kem_encapsulate, kem_decapsulate,
    hybrid_notarize, hybrid_verify,
)


def test_sha3_deterministic():
    assert sha3_256(b"test") == sha3_256(b"test")
    assert sha3_256(b"test") != sha3_256(b"test2")


def test_blake3_deterministic():
    assert blake3_hash(b"test") == blake3_hash(b"test")
    assert blake3_hash(b"test") != blake3_hash(b"test2")


def test_ml_dsa_sign_verify():
    pub, priv = ML_DSA_87.generate_keypair()
    msg = b"REAI notarizare test"
    sig = ML_DSA_87.sign(priv, msg)
    assert ML_DSA_87.verify(pub, msg, sig) is True
    assert ML_DSA_87.verify(pub, b"mesaj alterat", sig) is False


def test_sphincs_sign_verify():
    pub, priv = SPHINCS_PLUS.generate_keypair()
    msg = b"REAI notarizare test"
    sig = SPHINCS_PLUS.sign(priv, msg)
    assert SPHINCS_PLUS.verify(pub, msg, sig) is True
    assert SPHINCS_PLUS.verify(pub, b"mesaj alterat", sig) is False


def test_ml_kem_key_exchange():
    pub, priv = kem_generate_keypair()
    ciphertext, secret_sender = kem_encapsulate(pub)
    secret_receiver = kem_decapsulate(priv, ciphertext)
    assert secret_sender == secret_receiver
    assert len(secret_sender) == 32


def test_hybrid_notarize_and_verify():
    classical_priv = Ed25519PrivateKey.generate()
    classical_pub = classical_priv.public_key()
    pq_pub, pq_priv = ML_DSA_87.generate_keypair()

    content = b"Documentul REAI, versiunea finala"
    record = hybrid_notarize(content, classical_priv, ML_DSA_87, pq_priv)
    result = hybrid_verify(record, content, classical_pub, ML_DSA_87, pq_pub)

    assert result["overall_valid"] is True
    assert result["hash_intact"] is True
    assert result["classical_signature_valid"] is True
    assert result["pq_signature_valid"] is True


def test_hybrid_verify_fails_on_tampered_content():
    classical_priv = Ed25519PrivateKey.generate()
    classical_pub = classical_priv.public_key()
    pq_pub, pq_priv = ML_DSA_87.generate_keypair()

    content = b"Documentul original"
    record = hybrid_notarize(content, classical_priv, ML_DSA_87, pq_priv)

    tampered_content = b"Documentul alterat"
    result = hybrid_verify(record, tampered_content, classical_pub, ML_DSA_87, pq_pub)

    assert result["overall_valid"] is False
    assert result["hash_intact"] is False


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
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} trecute, {failed} esuate")
