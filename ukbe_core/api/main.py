"""
REAI-OS API - serviciu FastAPI care expune motorul UKBE, notary-ul clasic
si generarea/rezolvarea DID ca endpoint-uri HTTP.

NU e un sistem de operare in sensul clasic (kernel, procese, drivere) -
e un serviciu de retea peste biblioteca ukbe_core, rulabil pe orice
server care poate rula Python. Numele "OS" a fost clarificat cu userul
ca insemnand exact asta: un API rulabil independent, nu un kernel.

Ruleaza cu:
    uvicorn ukbe_core.api.main:app --host 0.0.0.0 --port 8000

Sesiunile motorului sunt tinute IN MEMORIE (dict simplu). La restart-ul
serverului, toate sesiunile active se pierd. Pentru productie, inlocuieste
cu un store persistent (Redis, DB) - marcat explicit ca limitare, nu ascuns.
"""
from __future__ import annotations
import uuid

from fastapi import FastAPI, HTTPException
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from ukbe_core.engine import UKBEEngine, UKBEConfig
from ukbe_core.calibration import recommend_beta_min
from ukbe_core import notary as notary_module
from ukbe_core import did as did_module
from ukbe_core import key_vault as key_vault_module

from .schemas import (
    EngineConfigRequest, SessionCreatedResponse, StepRequest, StepResponse,
    CalibrationRequest, CalibrationResponse,
    KeypairResponse, NotarizeRequest, NotarizeResponse, VerifyRequest, VerifyResponse,
    DIDGenerateResponse, DIDResolveResponse,
    EncryptKeyRequest, EncryptedKeyResponse, DecryptKeyRequest, DecryptKeyResponse,
)

app = FastAPI(
    title="REAI-OS API",
    description="Serviciu de retea peste motorul UKBE (Kuramoto+RSI), notary si DID. "
                "NU e un sistem de operare (kernel) - e un API HTTP.",
    version="0.1.0",
)

# store in-memory de sesiuni active ale motorului - vezi avertismentul din docstring
_sessions: dict[str, UKBEEngine] = {}


@app.get("/health")
def health():
    return {"status": "ok", "active_sessions": len(_sessions)}


# ---------- Motor (UKBE Engine) ----------

@app.post("/engine/session", response_model=SessionCreatedResponse)
def create_session(cfg: EngineConfigRequest):
    engine_cfg = UKBEConfig(**cfg.model_dump())
    engine = UKBEEngine(engine_cfg)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = engine
    return SessionCreatedResponse(session_id=session_id, config=cfg)


@app.post("/engine/session/{session_id}/step", response_model=StepResponse)
def step_session(session_id: str, req: StepRequest):
    engine = _sessions.get(session_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Sesiune inexistenta")
    result = engine.step(req.human_proxy_observation)
    return StepResponse(**result)


@app.delete("/engine/session/{session_id}")
def delete_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Sesiune inexistenta")


@app.get("/engine/sessions")
def list_sessions():
    return {"active_sessions": list(_sessions.keys())}


# ---------- Calibrare ----------

@app.post("/calibration/beta_min", response_model=CalibrationResponse)
def calibrate_beta_min(req: CalibrationRequest):
    result = recommend_beta_min(req.delta_omega_max, req.K_ext, req.safety_margin)
    return CalibrationResponse(**result)


# ---------- Notary (clasic, Ed25519) ----------

@app.post("/notary/keys/generate", response_model=KeypairResponse)
def generate_notary_keys():
    priv_bytes, pub_bytes = notary_module.generate_keypair()
    return KeypairResponse(private_key_hex=priv_bytes.hex(), public_key_hex=pub_bytes.hex())


@app.post("/notary/sign", response_model=NotarizeResponse)
def notarize(req: NotarizeRequest):
    try:
        priv_bytes = bytes.fromhex(req.private_key_hex)
        record = notary_module.notarize(req.intent, req.actor, req.qid, priv_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Cheie privata invalida: {e}")
    return NotarizeResponse(
        intent=record.intent, actor=record.actor, qid=record.qid,
        timestamp=record.timestamp, content_hash=record.content_hash,
        signature_hex=record.signature_hex,
    )


@app.post("/notary/verify", response_model=VerifyResponse)
def verify_notarization(req: VerifyRequest):
    record = notary_module.NotarizedRecord(
        intent=req.intent, actor=req.actor, qid=req.qid, timestamp=req.timestamp,
        content_hash=req.content_hash, signature_hex=req.signature_hex,
        witness_signatures=[],
    )
    try:
        pub_bytes = bytes.fromhex(req.public_key_hex)
        valid = notary_module.verify(record, pub_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Cheie publica invalida: {e}")
    return VerifyResponse(valid=valid)


# ---------- DID ----------

@app.post("/did/generate", response_model=DIDGenerateResponse)
def generate_did():
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    did_str = did_module.public_key_to_did_key(pub_bytes)
    return DIDGenerateResponse(
        did=did_str, private_key_hex=priv_bytes.hex(), public_key_hex=pub_bytes.hex(),
    )


@app.get("/did/resolve/{did:path}", response_model=DIDResolveResponse)
def resolve_did(did: str):
    try:
        doc = did_module.did_document(did)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DIDResolveResponse(did_document=doc)


# ---------- Key Vault (PBKDF2 + AES-GCM) ----------

@app.post("/vault/encrypt", response_model=EncryptedKeyResponse)
def encrypt_key(req: EncryptKeyRequest):
    try:
        priv_bytes = bytes.fromhex(req.private_key_hex)
    except ValueError:
        raise HTTPException(status_code=400, detail="private_key_hex invalid")
    enc = key_vault_module.encrypt_private_key(req.password, priv_bytes, req.iterations)
    return EncryptedKeyResponse(**enc.to_dict())


@app.post("/vault/decrypt", response_model=DecryptKeyResponse)
def decrypt_key(req: DecryptKeyRequest):
    enc = key_vault_module.EncryptedKey(req.salt, req.nonce, req.ciphertext, req.iterations)
    try:
        priv_bytes = key_vault_module.decrypt_private_key(req.password, enc)
    except key_vault_module.DecryptionError:
        raise HTTPException(status_code=401, detail="Parolă greșită sau date alterate")
    return DecryptKeyResponse(private_key_hex=priv_bytes.hex())
