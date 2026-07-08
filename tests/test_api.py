import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from ukbe_core.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_session_and_step():
    r = client.post("/engine/session", json={"N": 10, "beta_min": 0.25, "seed": 1})
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    r2 = client.post(f"/engine/session/{session_id}/step", json={"human_proxy_observation": 0.1})
    assert r2.status_code == 200
    body = r2.json()
    assert "RSI" in body and "Phi_extern" in body

    r3 = client.delete(f"/engine/session/{session_id}")
    assert r3.status_code == 200
    assert r3.json()["deleted"] is True


def test_step_on_nonexistent_session_returns_404():
    r = client.post("/engine/session/does-not-exist/step", json={"human_proxy_observation": 0.1})
    assert r.status_code == 404


def test_calibration_endpoint():
    r = client.post("/calibration/beta_min", json={"delta_omega_max": 0.4, "K_ext": 1.5, "safety_margin": 1.5})
    assert r.status_code == 200
    body = r.json()
    assert abs(body["threshold_beta_min"] - 0.4 / 1.5) < 1e-9
    assert body["recommended_beta_min"] > body["threshold_beta_min"]


def test_notary_full_roundtrip_via_api():
    keys = client.post("/notary/keys/generate").json()
    sign_resp = client.post("/notary/sign", json={
        "intent": "test prin API", "actor": "Mihai", "qid": "QID1",
        "private_key_hex": keys["private_key_hex"],
    })
    assert sign_resp.status_code == 200
    record = sign_resp.json()

    verify_resp = client.post("/notary/verify", json={
        **{k: record[k] for k in ["intent", "actor", "qid", "timestamp", "content_hash", "signature_hex"]},
        "public_key_hex": keys["public_key_hex"],
    })
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True


def test_notary_verify_fails_with_wrong_key():
    keys1 = client.post("/notary/keys/generate").json()
    keys2 = client.post("/notary/keys/generate").json()
    sign_resp = client.post("/notary/sign", json={
        "intent": "test", "actor": "Mihai", "qid": "QID1",
        "private_key_hex": keys1["private_key_hex"],
    }).json()

    verify_resp = client.post("/notary/verify", json={
        **{k: sign_resp[k] for k in ["intent", "actor", "qid", "timestamp", "content_hash", "signature_hex"]},
        "public_key_hex": keys2["public_key_hex"],  # cheia gresita
    })
    assert verify_resp.json()["valid"] is False


def test_did_generate_and_resolve_via_api():
    gen_resp = client.post("/did/generate")
    assert gen_resp.status_code == 200
    did_str = gen_resp.json()["did"]

    resolve_resp = client.get(f"/did/resolve/{did_str}")
    assert resolve_resp.status_code == 200
    doc = resolve_resp.json()["did_document"]
    assert doc["id"] == did_str


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
