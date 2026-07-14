# UKBE Core

**The REAI resonance engine — Kuramoto dynamics + Kalman intent estimation + adaptive α/β coupling — with a post-quantum notarization and safety stack around it. Every claim below is backed by a test that runs.**

*Română: [README.ro.md](README.ro.md) (detailed original).*

[![Tests](https://img.shields.io/badge/tests-102%2F102-brightgreen)]() [![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE) [![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()

## What this is

UKBE Core implements the alignment-dynamics model studied in the REAI framework and the accompanying paper on ghost sensitivity peaks (see [p6-adler-ghost-peak](https://github.com/amidigiart/p6-adler-ghost-peak)): N internal phase oscillators tracking a noisy estimate of human intent, with adaptive coupling weights governed by a coherence index, and a coupling floor calibrated from the phase-locking bifurcation — not guessed.

Around the engine, a verifiable-trust stack:

| Module | What it does | Tests |
|---|---|---|
| `engine.py` | Kuramoto + Kalman + adaptive α/β with corrected coherence formulas | ✔ |
| `calibration.py` | `recommend_beta_min()` — coupling floor from the Adler locking threshold with an explicit safety margin, `β_min ≥ m·Δω_max/K_ext` | ✔ |
| `notary.py` | SHA-256 hashing, Ed25519 signing, witnesses | 6/6 |
| `pq_crypto.py` | Post-quantum: ML-KEM-1024, ML-DSA-87, SPHINCS+ (NIST FIPS 203/204/205), SHA3-256, BLAKE3 | 7/7 |
| `did.py` | W3C `did:key` decentralized identifiers | 5/5 |
| `entropy_valve.py` | Blocks notarization when engine coherence is too low; KL-divergence safety check with 3-tier escalation (Safe Mode → Human-Approval-Only → Cold Shutdown) | 7/7 + 6/6 |
| `crisis_detection.py` | Acute-risk pattern detection with escalation to real resources — **not a clinical instrument**, see in-file warnings | 10/10 |
| `casp_signing.py` | Real covenant signing with ML-DSA-87 — replaces a legacy scheme whose signatures were forgeable without any key (verified empirically, then fixed) | 6/6 |
| `intent_dag.py` | Deterministic (regex, no LLM) intent-to-DAG conversion; rejected 8/8 tested prompt-injection attempts where a naive text executor leaked in 2/4 | 14/14 |
| `kce_graph.py` | Append-only knowledge-continuity DAG, Ed25519-signed nodes, multi-custodian axioms | 9/9 |
| `vector_consensus.py` | Lohe-model consensus on the unit sphere (tested alternative to an untrained-attention proposal that measured as no-op) | 8/8 |
| `key_vault.py` | PBKDF2 (250k iterations) + AES-GCM key storage with tamper detection | 6/6 |
| `api/` | FastAPI HTTP interface, tested with real requests | 7/7 |

## Quickstart

```bash
pip install -r requirements.txt
pytest tests/          # 102 passed
```

```python
from ukbe_core import UKBEEngine, UKBEConfig, recommend_beta_min

rec = recommend_beta_min(delta_omega_max=0.4, K_ext=1.5, safety_margin=1.5)
cfg = UKBEConfig(N=30, K_ext=1.5, beta_min=rec["recommended_beta_min"])
engine = UKBEEngine(cfg)

for z in your_human_proxy_stream:
    out = engine.step(z)          # -> RSI, Phi_extern, ...
```

## What is NOT validated — stated, not hidden

- Not tested at production scale (N ≤ 30 oscillators).
- Human-phase proxies are synthetic; whether real interaction signals admit a useful phase representation is the framework's central open problem (P1).
- The Kalman filter assumes a known, fixed observation noise R.
- `tezos_anchor.py` has not been tested against a live network.
- No legal/organizational framework (EU AI Act, GDPR, eIDAS 2.0, ISO 27001/42001, NIST) is "implemented" by this code — see [COMPLIANCE.md](COMPLIANCE.md) for the honest per-framework mapping.
- `invariant.py` derives deterministic keys from a fixed anchor — read its security warning before any real use.

## Design philosophy

Documented imperfection over simulated perfection. The test suite includes the unhappy paths: forged signatures that must fail, fabricated data that must be caught, coherent-but-wrong states scored as *more* dangerous than chaotic ones. The development record — including bugs found in our own formulas and externally supplied analyses rejected by measurement — is part of the project, not cleaned out of it.

## Methodology & lineage

This engine implements the **REAI** method. The methodology note, the verified self-correction of its 'universal equation' section, and the N-model coherence formula (WEAC) are documented in the value repository **[amidor-engine](https://github.com/amidigiart/amidor-engine)** (AGPL-3.0 / commercial). The reproduced scientific result behind it is open: [doi:10.5281/zenodo.21269201](https://doi.org/10.5281/zenodo.21269201) · [p6-adler-ghost-peak](https://github.com/amidigiart/p6-adler-ghost-peak).

## Related

- **Paper + reproduction:** [p6-adler-ghost-peak](https://github.com/amidigiart/p6-adler-ghost-peak) — the ghost-peak phenomenon, the Adler mechanism, and the calibration rule implemented here in `calibration.py`.
- **REAI framework document** (v0.7.2) — the broader theoretical context (publication in preparation).

## ⚖️ Open core & commercial licensing

**ukbe-core** is released under the permissive **[Apache-2.0](LICENSE)** license
© 2023–2026 Mihai Roșca. The foundational physics and alignment engine —
Kuramoto + Kalman + adaptive α/β with the derived β_min floor — is free forever:
use it, modify it, build on it, for research, education, or anything else.
The mathematics behind it is open and citable:
[doi:10.5281/zenodo.21269201](https://doi.org/10.5281/zenodo.21269201).

### What this repository deliberately does NOT contain

The **applied layer** — where the engine becomes products — is maintained in a
separate repository, **[amidor-engine](https://github.com/amidigiart/amidor-engine)**,
under an **AGPL-3.0 / commercial dual license**:

- **WEAC** (Weighted Ensemble Agreement Coherence) — the N-model
  confidence-and-abstention formula, with per-model reliability weighting and
  the hard numeric-conflict guard;
- **N-model anti-confabulation engines** (`DualEngine`, `EnsembleEngine`) with
  the REAI register gate wired into a production loop;
- **Arbitration Support** — the agreement/uncertainty meter for AI-assisted
  B2B arbitration (human-in-the-loop by construction);
- **Micro-grid synchronization tools** — the coupling-margin and recovery-time
  calculators applying the paper's calibration rule to grid stability;
- **the live REAI state monitor**, scam-shield, alerting, i18n, and the full
  deployable product stack (AmiDor).

None of that is a hidden switch inside this repo — it is genuinely separate
work, and this split is the business model, stated plainly.

### How the dual license works (read this before building a product)

- Building something **open-source**? AGPL lets you use amidor-engine freely —
  provided your product is open under compatible terms.
- Building **closed-source SaaS, enterprise systems, or commercial products**
  on the applied layer? AGPL's network clause requires you to open your entire
  service — or obtain a **commercial license** instead. That is the deal:
  open stays free, closed pays.

For commercial licensing or enterprise implementation of `amidor-engine`, see
its [COMMERCIAL.md](https://github.com/amidigiart/amidor-engine/blob/main/COMMERCIAL.md)
and contact **contact@kinderagi.com**.

*Honest engineering note: this base engine is a working reference
implementation. The mathematics does not break at scale (measured: N=1000,
RSI healthy), but the internal coupling here is the pedagogically-clear
pairwise **O(N²)** form, so large-N runs get slow — a performance property,
not a mathematical wall. The equivalent O(N) mean-field form is a standard
identity, not a secret. Also: phase-lock is **conditional** (K > Δω, the
Adler/SNIC threshold) per our own paper — anyone promising "unconditional"
synchronization is contradicting the physics. The commercial value of the
vault is real, shipped product code — not artificial limitations planted here.*
