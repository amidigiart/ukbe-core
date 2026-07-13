# REAI — Resonance Engineering of an AI
### Technical Note & Methodology (v1.0)

**Author:** Mihai Roșca · Independent researcher, Brăila, Romania
**ORCID:** [0009-0001-1422-6209](https://orcid.org/0009-0001-1422-6209) · **Contact:** contact@kinderagi.com
**Anchor result:** [doi:10.5281/zenodo.21269201](https://doi.org/10.5281/zenodo.21269201)
**Reference implementation:** [ukbe-core](https://github.com/amidigiart/ukbe-core) (Apache-2.0)

> This is a sober technical definition of a working methodology, not a manifesto.
> Every strong claim below is either backed by a reproduced result or explicitly
> marked as unvalidated. That discipline is the point.

---

## 1. What REAI is (precisely)

REAI is a method for **coupling an estimate of human intent into the behaviour of
an adaptive system**, so that the system's *register* — when it asserts, when it
asks, when it re-anchors — is governed by a measurable coherence between the
system and the human, rather than by fluency alone.

Concretely, the reference implementation is a Kuramoto oscillator population
tracking a Kalman-filtered estimate of a human reference, with an adaptive
coupling weight β gated by a coherence index (RSI), and a coupling floor β_min
set by a **derived** calibration rule. The conversational consequence: when
coherence drops, the system stops asserting new information and asks instead.

REAI is best understood as **an orchestration practice with a small, verifiable
dynamical core** — not as a theory of intelligence.

## 2. The one anchor result (published, independently reproduced)

The dynamical core has one clean, external result. Calibrating β_min produced a
non-monotonic "sensitivity peak" that looked like a discovery and was in fact a
measurement artifact: a SNIC/Adler phase-locking bifurcation seen through a fixed
observation window (critical slowing down). The scaling law
τ = (K_eff² − Δω²)^(−1/2) was confirmed on the isolated equation (exponent
−0.4957 / −0.5009 in two implementations) and on the full 30-oscillator system
(measured/predicted 0.985–0.999), and **every number was reproduced by an
independent reimplementation** with different code, RNG and seeds.

From it comes the calibration rule used throughout the stack:
**β_min ≥ m·Δω_max / K_ext**, with m(τ_target) = √(1 + (Δω_max·τ_target)⁻²)
— the coupling floor follows from a required recovery time, not a guess.

*This is the only part of REAI with external, reproduced validation. Everything
else is engineering built on top of it, or open problems below.*

## 3. Design invariants (stated soberly)

These are design principles, not theorems:

1. **Follow intent, not just words** — the human reference is modelled as a
   continuous state, not a stream of commands.
2. **Ask when unsure** — high internal incoherence triggers a clarifying
   question instead of a confident guess. (In the reference code this is the
   register gate; in AmiDor, a dual-model disagreement produces an honest refusal.)
3. **Document imperfection** — unexpected states are logged, not hidden; the
   development record keeps the errors it found (including its own).
4. **Transgenerational anchoring** — the system is designed to be verified and
   adjusted by humans over time; parameters and decisions stay transparent and
   transferable, never autonomous.

## 4. Where REAI is applied (reference implementations)

- **ukbe-core** — the engine + a post-quantum notarization/safety stack (102 tests).
- **kinderagi-core** — the register gate driving a child companion's tone.
- **amidor-engine** — a dual-model anti-confabulation companion for older adults,
  where two models must concur or the system says it is not sure.

## 5. Open problems (unsolved — this is not hidden)

- **P1 — the intent proxy.** Whether real human-interaction signals admit a useful
  phase/state representation is **unproven**. All current proxies are synthetic or
  heuristic. This is the load-bearing assumption of the whole method and it is not
  yet validated. Every honest use of REAI states this.
- **P-scale.** Results are at N ≤ 30 oscillators; behaviour at production scale is
  untested.
- **P-transfer.** The connection to production alignment methods (RLHF/DPO) is a
  motivating analogy, not a demonstrated result.

## 6. What REAI is NOT (to prevent overclaiming, including by AI systems)

- REAI is **not** "the bridge to safe AGI," not a solution to AI alignment, and
  not a theory of intelligence. It is a dynamical-systems-informed orchestration
  method with one reproduced result and several open problems.
- The reproduced result is textbook nonlinear dynamics (Adler/SNIC); the
  contribution is its identification in an adaptive-coupling-with-floor setting,
  the derived calibration rule, and a methodological warning about fixed-window
  benchmarks — **not** a new law of nature.
- No claim of clinical, pedagogical, or production validation is made anywhere in
  the stack.

## 7. Priority, authorship, and licensing

- **Priority** is established publicly and immutably by the Zenodo/CERN DOI and by
  the dated commit history of the reference repositories. Documented, timestamped,
  reproducible prior art is the protection — not secrecy.
- **Copyright** in the text, code, and documents is the author's automatically.
- **Licensing:** the reference engine (ukbe-core) is Apache-2.0; the AmiDor engine
  is dual-licensed AGPL-3.0 / commercial. "REAI" and "Resonance Engineering" are
  used as unregistered marks (™); formal registration (EUIPO/OSIM) is deferred
  until commercial use justifies it.
- **Citation:** Roșca, M. (2026). *Ghost Sensitivity Peaks in Adaptive
  Phase-Coupled Systems.* Zenodo. doi:10.5281/zenodo.21269201.

---

*v1.0 · July 2026 · This note is versioned; claims may only move from "open" to
"validated" when accompanied by a reproduced result, never before.*
