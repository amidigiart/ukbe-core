import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core.casp_signing import (
    generate_signing_keypair, sign_covenant, verify_covenant, canonical_json,
)


def test_canonical_json_ignores_key_order():
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}
    assert canonical_json(d1) == canonical_json(d2)


def test_sign_and_verify_roundtrip():
    pub, priv = generate_signing_keypair()
    data = {"type": "child-safe", "signatories": {"human": "parent:alice"}}
    sig = sign_covenant(data, pub, priv)

    assert sig.algorithm == "ml-dsa-87"
    assert verify_covenant(data, sig.to_string(), pub) is True


def test_verify_fails_with_wrong_public_key():
    pub1, priv1 = generate_signing_keypair()
    pub2, priv2 = generate_signing_keypair()
    data = {"type": "medical"}

    sig = sign_covenant(data, pub1, priv1)
    assert verify_covenant(data, sig.to_string(), pub2) is False


def test_verify_fails_on_tampered_data():
    pub, priv = generate_signing_keypair()
    original_data = {"type": "commercial", "amount": 100}
    sig = sign_covenant(original_data, pub, priv)

    tampered_data = {"type": "commercial", "amount": 999999}
    assert verify_covenant(tampered_data, sig.to_string(), pub) is False


def test_forgery_without_private_key_fails():
    """Testul central: replica exact scenariul de atac testat pe codul
    original - un 'atacator' care NU cunoaste nicio cheie privata reala
    incearca sa produca o semnatura valida. Aici, spre deosebire de
    implementarea originala, asta trebuie sa esueze intotdeauna."""
    pub_legit, priv_legit = generate_signing_keypair()
    data = {"covenant": "reguli reale, ale unui utilizator legitim"}

    real_signature = sign_covenant(data, pub_legit, priv_legit)

    # atacatorul, fara cheia privata reala, incearca cu o cheie inventata de el
    pub_attacker, priv_attacker = generate_signing_keypair()  # cheile lui, nu ale victimei
    forged_signature = sign_covenant(data, pub_attacker, priv_attacker)

    assert forged_signature.signature_hex != real_signature.signature_hex, (
        "semnaturile nu trebuie sa fie identice - inseamna ca cheia chiar conteaza"
    )
    # verificarea cu cheia publica a victimei trebuie sa respinga semnatura atacatorului
    assert verify_covenant(data, forged_signature.to_string(), pub_legit) is False


def test_malformed_signature_string_rejected():
    pub, priv = generate_signing_keypair()
    data = {"type": "creative"}

    assert verify_covenant(data, "not-a-real-signature-format", pub) is False
    assert verify_covenant(data, "ml-dsa-87:not-valid-hex-zzz", pub) is False


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
