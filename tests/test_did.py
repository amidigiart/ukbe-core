import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from ukbe_core.did import public_key_to_did_key, did_key_to_public_key, did_document


def _fresh_pubkey():
    priv = Ed25519PrivateKey.generate()
    return priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


def test_did_has_correct_prefix():
    pub = _fresh_pubkey()
    did = public_key_to_did_key(pub)
    assert did.startswith("did:key:z6Mk"), "prefixul standard W3C pentru Ed25519 e z6Mk"


def test_did_roundtrip():
    pub = _fresh_pubkey()
    did = public_key_to_did_key(pub)
    recovered = did_key_to_public_key(did)
    assert recovered == pub


def test_different_keys_give_different_dids():
    did1 = public_key_to_did_key(_fresh_pubkey())
    did2 = public_key_to_did_key(_fresh_pubkey())
    assert did1 != did2


def test_did_document_structure():
    pub = _fresh_pubkey()
    did = public_key_to_did_key(pub)
    doc = did_document(did)
    assert doc["id"] == did
    assert doc["@context"] == "https://www.w3.org/ns/did/v1"
    assert len(doc["verificationMethod"]) == 1


def test_invalid_did_rejected():
    try:
        did_key_to_public_key("not:a:valid:did")
        assert False, "trebuia sa arunce ValueError"
    except ValueError:
        pass


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
    print(f"\n{passed} trecute, {failed} esuate")
