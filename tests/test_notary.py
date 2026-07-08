import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core import notary


def test_hash_is_deterministic():
    priv, pub = notary.generate_keypair()
    r1 = notary.notarize("intentia mea", "Mihai", "QID123", priv, timestamp="2026-07-03T00:00:00Z")
    r2 = notary.notarize("intentia mea", "Mihai", "QID123", priv, timestamp="2026-07-03T00:00:00Z")
    assert r1.content_hash == r2.content_hash, "acelasi input trebuie sa dea acelasi hash"


def test_hash_changes_with_content():
    priv, pub = notary.generate_keypair()
    r1 = notary.notarize("intentia A", "Mihai", "QID123", priv, timestamp="2026-07-03T00:00:00Z")
    r2 = notary.notarize("intentia B", "Mihai", "QID123", priv, timestamp="2026-07-03T00:00:00Z")
    assert r1.content_hash != r2.content_hash


def test_signature_verifies_with_correct_key():
    priv, pub = notary.generate_keypair()
    record = notary.notarize("test", "Mihai", "QID123", priv)
    assert notary.verify(record, pub) is True


def test_signature_fails_with_wrong_key():
    priv, pub = notary.generate_keypair()
    _, wrong_pub = notary.generate_keypair()
    record = notary.notarize("test", "Mihai", "QID123", priv)
    assert notary.verify(record, wrong_pub) is False


def test_tampered_content_fails_verification():
    priv, pub = notary.generate_keypair()
    record = notary.notarize("test original", "Mihai", "QID123", priv)
    record.intent = "test alterat"  # cineva modifica textul dupa semnare
    assert notary.verify(record, pub) is False, "continutul alterat trebuie sa esueze la verificare"


def test_witness_signature():
    priv, pub = notary.generate_keypair()
    w_priv, w_pub = notary.generate_keypair()
    record = notary.notarize("test", "Mihai", "QID123", priv)
    record = notary.add_witness(record, "witness_1", w_priv)
    assert notary.verify_witness(record, "witness_1", w_pub) is True
    assert notary.verify_witness(record, "witness_necunoscut", w_pub) is False


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
