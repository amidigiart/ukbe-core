from pydantic import BaseModel, Field


class EngineConfigRequest(BaseModel):
    N: int = Field(30, ge=1, le=1000)
    dt: float = 0.02
    K_int: float = 1.2
    K_ext: float = 1.5
    beta_min: float = 0.20
    rsi_window: int = 50
    omega_mean: float = 1.0
    omega_std: float = 0.05
    kalman_R: float = 0.05
    seed: int | None = None


class SessionCreatedResponse(BaseModel):
    session_id: str
    config: EngineConfigRequest


class StepRequest(BaseModel):
    human_proxy_observation: float


class StepResponse(BaseModel):
    t: float
    RSI: float
    Phi_intern: float
    Phi_extern: float
    psi: float
    alpha: float
    beta: float
    theta_human_est: float


class CalibrationRequest(BaseModel):
    delta_omega_max: float = Field(..., gt=0)
    K_ext: float = Field(..., gt=0)
    safety_margin: float = 1.5


class CalibrationResponse(BaseModel):
    delta_omega_max: float
    K_ext: float
    threshold_beta_min: float
    recommended_beta_min: float
    safety_margin: float
    warning: str


class KeypairResponse(BaseModel):
    private_key_hex: str
    public_key_hex: str
    warning: str = (
        "Serverul NU stocheaza aceasta cheie privata. Salveaz-o tu, in siguranta. "
        "Acest tip de generare pe server e potrivit doar pentru self-hosting de incredere, "
        "nu pentru servicii multi-tenant expuse public."
    )


class NotarizeRequest(BaseModel):
    intent: str
    actor: str
    qid: str
    private_key_hex: str


class NotarizeResponse(BaseModel):
    intent: str
    actor: str
    qid: str
    timestamp: str
    content_hash: str
    signature_hex: str


class VerifyRequest(BaseModel):
    intent: str
    actor: str
    qid: str
    timestamp: str
    content_hash: str
    signature_hex: str
    public_key_hex: str


class VerifyResponse(BaseModel):
    valid: bool


class DIDGenerateResponse(BaseModel):
    did: str
    private_key_hex: str
    public_key_hex: str
    warning: str = (
        "Serverul NU stocheaza cheia privata. Salveaz-o tu, in siguranta."
    )


class DIDResolveResponse(BaseModel):
    did_document: dict


class EncryptKeyRequest(BaseModel):
    password: str
    private_key_hex: str
    iterations: int = 250_000


class EncryptedKeyResponse(BaseModel):
    salt: str
    nonce: str
    ciphertext: str
    iterations: int


class DecryptKeyRequest(BaseModel):
    password: str
    salt: str
    nonce: str
    ciphertext: str
    iterations: int


class DecryptKeyResponse(BaseModel):
    private_key_hex: str
