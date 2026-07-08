import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core.key_vault import (
    encrypt_private_key, decrypt_private_key, EncryptedKey, DecryptionError,
)
from ukbe_core.notary import generate_keypair


def test_roundtrip_correct_password():
    priv, pub = generate_keypair()
    enc = encrypt_private_key("parola-puternica-123", priv, iterations=10_000)  # iteratii mici doar pt viteza testului
    decrypted = decrypt_private_key("parola-puternica-123", enc)
    assert decrypted == priv


def test_wrong_password_fails():
    priv, pub = generate_keypair()
    enc = encrypt_private_key("parola-corecta", priv, iterations=10_000)
    try:
        decrypt_private_key("parola-gresita", enc)
        assert False, "ar fi trebuit sa esueze cu parola gresita"
    except DecryptionError:
        pass


def test_tampered_ciphertext_detected():
    """Testul critic: AES-GCM trebuie sa detecteze alterarea datelor,
    nu doar parola gresita - asta e diferenta fata de criptare simpla."""
    priv, pub = generate_keypair()
    enc = encrypt_private_key("parola-corecta", priv, iterations=10_000)

    # alterez un singur caracter din ciphertext
    tampered_hex = list(enc.ciphertext_hex)
    idx = 0
    tampered_hex[idx] = '0' if tampered_hex[idx] != '0' else '1'
    tampered = EncryptedKey(enc.salt_hex, enc.nonce_hex, "".join(tampered_hex), enc.iterations)

    try:
        decrypt_private_key("parola-corecta", tampered)
        assert False, "ar fi trebuit sa detecteze alterarea ciphertext-ului"
    except DecryptionError:
        pass  # comportament corect - AES-GCM a detectat manipularea


def test_salt_and_nonce_unique_per_call():
    priv, pub = generate_keypair()
    enc1 = encrypt_private_key("aceeasi-parola", priv, iterations=10_000)
    enc2 = encrypt_private_key("aceeasi-parola", priv, iterations=10_000)
    assert enc1.salt_hex != enc2.salt_hex, "salt-ul trebuie sa fie unic la fiecare criptare"
    assert enc1.nonce_hex != enc2.nonce_hex, "nonce-ul trebuie sa fie unic la fiecare criptare"
    assert enc1.ciphertext_hex != enc2.ciphertext_hex, "ciphertext diferit, desi textul clar e identic"


def test_serialization_roundtrip():
    priv, pub = generate_keypair()
    enc = encrypt_private_key("parola", priv, iterations=10_000)
    as_dict = enc.to_dict()
    restored = EncryptedKey.from_dict(as_dict)
    decrypted = decrypt_private_key("parola", restored)
    assert decrypted == priv


def test_works_with_larger_keys_like_dilithium():
    """Verific ca functioneaza si cu chei mai mari (Dilithium are chei
    private de ordinul a mii de bytes, nu doar 32 ca Ed25519)."""
    fake_large_key = os.urandom(4032)  # dimensiune aproximativa cheie privata ML-DSA-87
    enc = encrypt_private_key("parola", fake_large_key, iterations=10_000)
    decrypted = decrypt_private_key("parola", enc)
    assert decrypted == fake_large_key


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
