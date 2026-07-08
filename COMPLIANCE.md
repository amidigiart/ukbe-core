# Maparea onestă pe standarde și reglementări

**Acest document NU e o declarație de conformitate.** Nicio bibliotecă de cod nu poate face un sistem "conform" cu o reglementare — conformitatea vine din audit extern, documentație de proces, evaluări de risc, și, pentru multe din cadrele de mai jos, implicarea unui jurist. Prezentarea acestui pachet ca fiind deja conform, unui investitor sau auditor, ar fi exact genul de afirmație nesusținută pe care am respins-o de mai multe ori azi când a venit din alte surse.

Ce oferă acest document: pentru fiecare cadru din listă, ce **măsură tehnică** există deja (dacă există) și ce **rămâne, explicit, de făcut** — de obicei de oameni, nu de cod.

## Standarde tehnice — au echivalent direct în cod

| Standard | Ce există în pachet | Status |
|---|---|---|
| **SHA-3** | `pq_crypto.sha3_256()` | Implementat, testat |
| **BLAKE3** | `pq_crypto.blake3_hash()` | Implementat, testat |
| **ML-KEM-1024 (Kyber1024)** | `pq_crypto.kem_*` | Implementat, testat |
| **ML-DSA (Dilithium)** | `pq_crypto.ML_DSA_87` | Implementat, testat |
| **SPHINCS+** | `pq_crypto.SPHINCS_PLUS` | Implementat, testat |
| **W3C DID** | `did.py` (metoda did:key) | Implementat, testat |
| **I18N** | `i18n.py` | Implementat, testat (schelet minimal — nu framework complet) |

Aceste șapte sunt verificabile direct — rulează testele din `tests/`.

## Reglementări UE — NU au echivalent în cod, necesită proces legal/organizațional

| Cadru | Ce cere de fapt | Ce NU poate face codul |
|---|---|---|
| **EU AI Act** | Clasificare de risc, documentație tehnică, evaluare de conformitate, registru UE (pentru sisteme cu risc înalt), transparență către utilizatori | Codul poate *susține* trasabilitatea (notary-ul ajută la audit), dar clasificarea de risc și evaluarea de conformitate sunt procese, nu funcții |
| **GDPR** | Bază legală pentru procesare, DPIA (evaluare de impact), drepturile persoanei vizate (acces, ștergere, portabilitate), DPO dacă e cazul | Acest pachet nu procesează date cu caracter personal ale unor terți — dacă va procesa, GDPR se aplică integral și necesită DPIA separată |
| **eIDAS 2.0** | Semnătură electronică calificată necesită un furnizor de servicii de încredere calificat (QTSP), acreditat, nu doar Ed25519/ML-DSA rulate local | Semnăturile din `notary.py`/`pq_crypto.py` sunt criptografic valide, dar **nu sunt semnături electronice calificate** în sensul eIDAS fără un QTSP |
| **Data Act (UE) 2023/2854** | Drepturi de acces la date generate de produse conectate, portabilitate, interoperabilitate contractuală | Nu se aplică direct unui motor de calcul fără produs conectat cu utilizatori finali — de evaluat dacă/când apare un asemenea produs |
| **EU Cyber Resilience Act (CRA)** | Cerințe de securitate pe tot ciclul de viață al produsului, raportare de vulnerabilități, marcaj CE pentru produse cu elemente digitale | Codul poate fi un input pentru evaluarea CRA, dar conformitatea CRA e la nivel de *produs* comercializat, nu de bibliotecă |
| **EN 18031** | Cerințe de securitate cibernetică pentru echipamente radio (relevant dacă produsul include hardware radio) | Nu se aplică — acest pachet e software pur, fără componentă radio |

## Standarde ISO — necesită certificare organizațională, nu doar cod

| Standard | Ce cere | Ce NU poate face codul |
|---|---|---|
| **ISO/IEC 27001** | Sistem de management al securității informației (SMSI) — politici, roluri, audit intern, îmbunătățire continuă | E un sistem organizațional certificat de un auditor acreditat, nu o proprietate a codului |
| **ISO/IEC 27018** | Protecția datelor cu caracter personal în cloud — extensie a 27001/27002 | Aceleași observații ca 27001 — organizațional, nu tehnic |
| **ISO/IEC 42001** | Sistem de management pentru AI — guvernanță, evaluare de risc pe tot ciclul de viață | Organizațional; codul poate fi *un input* documentat pentru un asemenea sistem |
| **ISO/IEC 23894** | Ghid de management al riscului pentru AI | Ghid de proces, nu specificație tehnică de implementat |
| **NIST (cadru general)** | Depinde care — NIST AI RMF (management de risc AI) e cel mai probabil relevant aici; e un cadru de proces, similar cu ISO 42001 | Proces, nu cod |

## Ce recomand, concret, în ordine

1. **Nu prezenta acest pachet ca fiind "conform"** cu niciuna din reglementările/standardele din a doua și a treia secțiune, până nu există documentația de proces și, unde e cazul, auditul extern corespunzător.
2. **Componentele tehnice din prima secțiune pot fi menționate onest** ca măsuri tehnice existente și testate — ele chiar sunt utile ca *input* pentru un viitor audit ISO 42001 sau pentru documentația tehnică cerută de EU AI Act, dar nu sunt substitute pentru acel proces.
3. Dacă intenția reală e prezentarea către investitori/auditori: recomand consultarea unui jurist specializat în reglementare AI/date UE înainte de orice afirmație de conformitate scrisă. Nu sunt avocat și acest document nu e consultanță juridică — e doar o hartă onestă a ce separă codul de conformitate.
