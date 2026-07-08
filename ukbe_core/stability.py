"""
Verificare de stabilitate pentru sisteme multi-strat cuplate liniar
(cf. Sectiunea 22 a documentului REAI).

Model: dPsi_i/dt = -lambda_i*Psi_i + sum_j beta_ij*(Psi_j-Psi_i) + gamma_i*Ancora

Conditie suficienta de stabilitate (Teorema Gershgorin, verificata empiric
in Sectiunea 22.3): lambda_i > 0 pentru toti i, indiferent de beta_ij >= 0,
oricat de mari sau asimetrice.

ATENTIE - conditie RESPINSA (Sectiunea 22.2, pastrata aici doar ca sa nu
fie reintrodusa din greseala): lambda_i + sum_j(beta_ij) > 0 NU e suficienta.
Exista contraexemplu confirmat (lambda1=-0.5, lambda2=-0.85, beta=1.2 simetric
-> o valoare proprie = +0.6877, desi conditia era satisfacuta pt ambele noduri).
"""
import numpy as np


def build_coupling_matrix(lam: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """Construieste matricea M pentru sistemul dPsi/dt = M @ Psi (+ forcing).
    lam: array (N,) - coeficientii de amortizare lambda_i
    beta: array (N,N) - cuplaj beta_ij >= 0, diagonala ignorata
    """
    N = len(lam)
    M = np.zeros((N, N))
    for i in range(N):
        M[i, i] = -lam[i] - sum(beta[i, k] for k in range(N) if k != i)
        for j in range(N):
            if j != i:
                M[i, j] = beta[i, j]
    return M


def is_stable_gershgorin(lam: np.ndarray) -> bool:
    """Conditia suficienta si corecta (Sectiunea 22.3): lambda_i > 0 pentru toti.
    Nu necesita calculul valorilor proprii si e valabila indiferent de beta>=0."""
    return bool(np.all(np.asarray(lam) > 0))


def verify_eigenvalues(lam: np.ndarray, beta: np.ndarray) -> dict:
    """Verificare directa (nu doar conditia suficienta) - calculeaza
    valorile proprii reale ale sistemului, pentru audit/validare."""
    M = build_coupling_matrix(lam, beta)
    eig = np.linalg.eigvals(M)
    return {
        "eigenvalues_real": eig.real.tolist(),
        "max_real_part": float(eig.real.max()),
        "stable": bool(np.all(eig.real < 0)),
        "gershgorin_predicts_stable": is_stable_gershgorin(lam),
    }
