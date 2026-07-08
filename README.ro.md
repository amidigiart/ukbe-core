# UKBE Core

Motorul REAI (Kuramoto + estimare Kalman + ponderi α/β dinamice), cu toate
corecțiile validate empiric în sesiunea de dezvoltare (iulie 2026, documentul
REAI v0.7.2, Secțiunile 22, 25, 26).

## Instalare

```bash
pip install numpy
# fara alte dependinte externe
```

## Utilizare rapidă

```python
from ukbe_core import UKBEEngine, UKBEConfig, recommend_beta_min

# 1. calibrează beta_min corect, pe baza discrepanței de frecvență anticipate
rec = recommend_beta_min(delta_omega_max=0.4, K_ext=1.5, safety_margin=1.5)
print(rec["recommended_beta_min"])  # 0.4 (nu o valoare fixă arbitrară)

# 2. construiește motorul
cfg = UKBEConfig(N=30, K_ext=1.5, beta_min=rec["recommended_beta_min"])
engine = UKBEEngine(cfg)

# 3. rulează pas cu pas, cu observații (proxy) ale fazei umane
for z in your_human_proxy_stream:
    result = engine.step(z)
    print(result["RSI"], result["Phi_extern"])
```

## Ce e VALIDAT (testat, cu teste care rulează — vezi `tests/`, 102/102 trec)

- Formula Φ_extern corectă (nu degenerată)
- Planșeul β_min respectat, indiferent de RSI
- Pragul de blocare de fază, verificat empiric față de predicția analitică Adler
- Condiția de stabilitate Gershgorin (λᵢ>0), inclusiv contraexemplul care respinge alternativa greșită
- **Notary** (`notary.py`): hash SHA-256, semnătură Ed25519, verificare, martori — 6/6 teste
- **Criptografie post-cuantică** (`pq_crypto.py`): SHA3-256, BLAKE3, ML-KEM-1024 (Kyber1024), ML-DSA-87 (Dilithium), SPHINCS+ — toate NIST FIPS 203/204/205, testate real — 7/7 teste
- **DID** (`did.py`): metoda `did:key`, conform W3C DID Core — 5/5 teste
- **i18n** (`i18n.py`): schelet minimal RO/EN
- **API HTTP** (`api/`): FastAPI, pornit real cu `uvicorn`, verificat cu cereri HTTP reale — 7/7 teste
- **Invariant + KDF** (`invariant.py`): derivare deterministă de chei din ancoră fixă — 3/3 teste (**vezi avertismentul de securitate din fișier** — nu folosi pentru chei secrete reale fără citirea lui)
- **Entropy Valve + DataCore snapshot** (`entropy_valve.py`): blochează sigilarea când coerența motorului e prea scăzută, atașează starea UKBE (Φ, RSI, H, θ) la fiecare notarizare — 7/7 teste, inclusiv testul de blocare reală (nu doar cazul fericit). **Actualizat**: `kl_safety_check()` adaugă un al doilea nivel de verificare — KL divergence dinamică între distribuția de faze curentă și un baseline aprobat, cu 3 niveluri ierarhice (Safe Mode → Human-Approval-Only → Cold Shutdown). **Decizie de design testată și documentată explicit**: un sistem blocat coerent dar defazat 180° de la baseline primește un scor mai sever decât unul complet haotic — intenționat, pentru că "încrezător dar greșit" e considerat mai riscant decât "nesigur" într-un context de siguranță. 6/6 teste noi.
- **Crisis Detection v0** (`crisis_detection.py`): primul pas din Safety Layer (roadmap-ul din pitch deck) — detecție de pattern-uri de risc acut, escaladare către resurse reale, întrerupe fluxul de companion la semnal ACUTE — 10/10 teste, inclusiv testul critic de fals-pozitiv pe limbaj figurativ. **NU e instrument clinic — vezi avertismentele din fișier înainte de orice folosire reală.**
- **Key Vault** (`key_vault.py`): PBKDF2 (250.000 iterații) + AES-GCM pentru stocarea sigură a cheilor private cu parolă — portat din pattern-ul validat primit de la Mercury 2/Inception Labs — 6/6 teste, inclusiv detecția de alterare a datelor (nu doar parolă greșită). Expus și prin API (`/vault/encrypt`, `/vault/decrypt`).
- **CASP Signing** (`casp_signing.py`): semnare reală de covenant-uri, folosind ML-DSA-87 (Dilithium5) — înlocuiește complet schema de semnare CASP originală (unde parametrul `private_key` nu era folosit deloc în calcul — verificat empiric că oricine putea falsifica semnătura fără nicio cheie) — 6/6 teste, inclusiv falsificare fără cheie privată (acum eșuează, cum trebuie).
- **Semantic Validator v1** (`semantic_validator.py`): validare "non_harm" cu context de excepție — repară bug-ul găsit empiric în CASP original, unde un răspuns de escaladare de criză (conținând necesar cuvinte ca "suicide"/"harm") era clasificat drept conținut dăunător — 5/5 teste, inclusiv testul exact cu răspunsul de siguranță din `crisis_detection.py`. **Rămâne v0 euristic — vezi limitările din fișier.**
- **KCE Graph** (`kce_graph.py`): prototip pentru continuitatea cunoștințelor peste schimbarea de model (Secțiunea 19 REAI) — graf DAG append-only, noduri semnate Ed25519. Noduri "fact" (o semnătură) vs "axiom" (necesită TOȚI custozii desemnați — multi-sig, niciun punct unic de eșec pentru valorile centrale). 9/9 teste, inclusiv: respingerea unui axiom fără toți custozii, și un strămoș alterat care strică lineage-ul descendentului fără să invalideze nodul copil izolat. **Onest: căutarea e pe etichete (tags), NU semantică — niciun model de embeddings inclus.**
- **Intent DAG** (`intent_dag.py`): conversie DETERMINISTĂ (regex, fără AI) a unei intenții cu vocabular restrâns într-un DAG semnat — descoperire empirică (nu teoretică): un executor care primește doar DAG-ul a respins 8/8 încercări de injecție de prompt testate direct (linie nouă falsă de "sistem", propoziție secundară ascunsă, destinatar strecurat în câmpul greșit), pe când un executor naiv pe text brut a scurs adresa atacatorului în 2/4 cazuri. **Limită de scop confirmată tot empiric**: funcționează doar pentru vocabular mic, cunoscut dinainte — dacă domeniul are nevoie de intenție liberă convertită de un LLM, vulnerabilitatea se mută în acel pas, nu dispare. 14/14 teste.
- **Vector Consensus** (`vector_consensus.py`): alternativă testată și preferată față de o propunere externă (DeepSeek) de "consens prin cross-attention" — verificat direct: atenția neantrenată nu adaugă nimic dincolo de similaritatea cosinus brută (diferență constantă ~0.05, indiferent de conținut), pentru că nu exista nicio buclă de antrenare în propunere. Modelul Lohe (generalizare stabilită a Kuramoto la sfera unitate în Rⁿ, aceeași familie matematică deja validată în `engine.py`) convergere real testată: 0.004→0.95 în 30 de pași, plus recuperare după perturbare (0.78→0.004→0.77). Formula vectorizată verificată echivalentă cu suma directă la precizia mașinii (1e-16). 8/8 teste.

## Ce NU e validat — onest, nu ascuns

- **Nu a fost testat la scară de producție.** Testele rulează la N≤30 oscilatori.
- **Proxy-urile pentru faza umană rămân sintetice.** Problema P1 din documentul REAI nu e rezolvată aici.
- **Filtrul Kalman presupune `R` cunoscut și fix** — cf. Secțiunea 25.4.
- **`tezos_anchor.py` NU a fost testat live** — vezi avertismentul din fișier.
- **Niciun cadru legal sau standard organizațional (EU AI Act, GDPR, eIDAS 2.0, Data Act, CRA, ISO 27001/27018/42001/23894, NIST) nu e "implementat" de acest cod** — vezi `COMPLIANCE.md` pentru maparea onestă, cadru cu cadru, a ce înseamnă asta de fapt.
- **"Comutarea la internetul cuantic" nu există ca funcție** — vezi `QUANTUM_READINESS.md` pentru explicația de ce, și ce e de fapt relevant (criptografie post-cuantică, deja implementată mai sus).

## Structură

```
ukbe_core/
  engine.py         - motorul de simulare (Kuramoto + Kalman + alpha/beta)
  stability.py       - verificare de stabilitate (Gershgorin)
  calibration.py     - calibrare beta_min (pragul Adler)
  notary.py           - hash + semnatura Ed25519 (clasic)
  pq_crypto.py         - SHA3, BLAKE3, ML-KEM-1024, ML-DSA, SPHINCS+ (post-cuantic)
  did.py                - W3C DID (did:key)
  i18n.py                - mesaje RO/EN
  tezos_anchor.py         - ancorare blockchain, NETESTAT LIVE
tests/                     - 24 teste, toate trec
COMPLIANCE.md               - maparea onesta pe standarde/reglementari (NU o declaratie de conformitate)
QUANTUM_READINESS.md         - de ce "internet cuantic" != cod, si ce e de fapt relevant
```

## API HTTP (REAI-OS ca serviciu)

**Clarificare de nume:** "REAI-OS" înseamnă aici un serviciu de rețea (FastAPI), NU un sistem de operare cu kernel. Rulabil pe orice server care poate rula Python.

```bash
pip install fastapi uvicorn
uvicorn ukbe_core.api.main:app --host 0.0.0.0 --port 8000
```

Endpoint-uri (verificate real, pornit efectiv cu uvicorn, nu doar prin TestClient):

| Endpoint | Metodă | Funcție |
|---|---|---|
| `/health` | GET | status serviciu |
| `/engine/session` | POST | creează o sesiune de motor (Kuramoto+RSI) |
| `/engine/session/{id}/step` | POST | avansează un pas, cu o observație proxy a fazei umane |
| `/engine/session/{id}` | DELETE | șterge sesiunea |
| `/calibration/beta_min` | POST | recomandare β_min, pe baza pragului Adler |
| `/notary/keys/generate` | POST | generează pereche de chei Ed25519 (nu stocată) |
| `/notary/sign` | POST | notarizează (hash+semnătură) |
| `/notary/verify` | POST | verifică o notarizare |
| `/did/generate` | POST | generează un DID nou (`did:key`) |
| `/did/resolve/{did}` | GET | rezolvă un DID la documentul lui |

**Limitare importantă, nu ascunsă:** sesiunile motorului sunt ținute în memorie (dict simplu) — la restart-ul serverului, se pierd. Pentru producție, înlocuiește cu un store persistent (Redis/DB). Cheile private NU sunt stocate de server niciodată — responsabilitatea păstrării lor e a clientului.

## Pași recomandați pentru Tezos, în ordine



1. Instalează `pytezos` separat: `pip install pytezos`
2. Scrie/deployează un contract minimal de ancorare (vezi template comentat în `tezos_anchor.py`) — **pe Ghostnet, nu pe mainnet**
3. Obține XTZ de test de la un faucet Ghostnet
4. Rulează `anchor_hash_tezos()` cu `rpc_url` către Ghostnet, verifică manual pe `tzkt.io/ghostnet` că operația a ajuns pe lanț
5. Doar după ce (1)-(4) funcționează constant, repetat, ia în calcul mainnet

---
Proprietate intelectuală: Mihai Roșca
