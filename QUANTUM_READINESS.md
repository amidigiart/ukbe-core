# De ce nu există "linii de cod pentru comutarea la internetul cuantic"

## Răspunsul scurt

Nu pentru că e greu de scris — ci pentru că cererea descrie o categorie greșită de lucru. Internetul cuantic nu e un protocol software peste care rulează aplicația ta. E un **strat fizic diferit**.

## Ce e, de fapt, "internetul cuantic"

Rețele care transmit stări cuantice (fotoni încâlciți/entangled) între noduri, pentru:
- **QKD (Quantum Key Distribution)** — distribuție de chei cu securitate garantată de legile fizicii, nu de dificultate computațională
- **Repetoare cuantice** — pentru a extinde distanța fără să distrugi starea cuantică (nu poți "amplifica" un semnal cuantic ca pe unul clasic — teorema no-cloning)
- **Rețele de entanglement** — pentru aplicații ca teleportarea cuantică a informației (nu date, stări)

Toate astea cer **hardware dedicat**: surse de fotoni unici, fibră optică specializată sau linkuri satelitare, detectoare criogenice în multe implementări. Nu există un driver software care "activează" asta pe infrastructura TCP/IP existentă.

## Ce ESTE relevant, real, și deja construit în acest pachet

Ce industria numește de fapt "pregătire cuantică" (quantum readiness) nu înseamnă conectare la internetul cuantic — înseamnă **rezistență la calculatoare cuantice**, adică:

Un calculator cuantic suficient de puternic ar putea sparge criptografia clasică (RSA, curbe eliptice — inclusiv Ed25519) prin algoritmul lui Shor. Răspunsul industriei (NIST, ENISA) nu e "conectează-te la internetul cuantic", ci **înlocuiește algoritmii vulnerabili cu algoritmi rezistenți la atac cuantic, rulați pe internetul clasic de azi**.

Asta chiar am construit, în `pq_crypto.py`:
- **ML-KEM-1024** (Kyber1024) — schimb de chei rezistent la atac cuantic
- **ML-DSA-87** (Dilithium) și **SPHINCS+** — semnături rezistente la atac cuantic
- Ambele standardizate NIST (FIPS 203, 204, 205) în 2024, testate real în acest pachet

## Recomandarea practică

„Comutarea" pe care o poți face azi, cu sens, e exact agilitatea criptografică din `pq_crypto.py` — susții simultan Ed25519 (rapid, azi) și ML-DSA/SPHINCS+ (rezistent la cuantic), fără să depinzi de nicio infrastructură de rețea specială. Când (și dacă) internetul cuantic devine infrastructură comercială disponibilă, integrarea lui va fi un proiect de infrastructură de rețea separat, nu o linie de cod într-un modul de criptografie.
