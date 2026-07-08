"""
UKBE Core - Unified Kuramoto-RSI Bridging Engine
==================================================

Implementarea motorului REAI (Kuramoto + estimare Kalman a intentiei umane +
ponderi alpha/beta dinamice), cu toate corectiile validate empiric in
sesiunea de dezvoltare din iulie 2026.

CORECTII APLICATE FATA DE FORMULAREA INITIALA (v0.7 a documentului REAI):

1. Phi_extern corectat (Sectiunea 25.1 a documentului):
   formula originala |e^(i*psi)| e degenerata (= 1 mereu, orice psi).
   Corectat la (1+cos(psi))/2, care variaza real in [0,1].

2. beta_min - planseu minim pentru ponderea umana (Sectiunea 25.3):
   fara el, sistemul se poate "orbi" la dezalinierea cu omul quando
   RSI e ridicat (Problema P2).

3. Calibrare beta_min pe baza mecanismului Adler (Sectiunea 26):
   beta_min trebuie sa satisfaca K_eff = beta_min*K_ext >= 1.5*Delta_omega_max,
   nu o valoare fixa arbitrara - vezi calibration.py.

STATUS DE VALIDARE (onest, nu "garantat"):
- Testat pana la N=30 oscilatori interni, in aceasta sesiune.
- NU a fost testat la N=10.000 sau la scara de productie.
- Stabilitatea interna (Kuramoto) e garantata doar daca se respecta
  conditia Gershgorin din stability.py - NU e automata.
- Proxy-urile pentru theta_uman raman sintetice - Problema P1 din
  documentul REAI (Sectiunea 8) NU e rezolvata de acest cod.
"""
from dataclasses import dataclass, field
import numpy as np


@dataclass
class UKBEConfig:
    N: int = 30                    # numar oscilatori interni
    dt: float = 0.02
    K_int: float = 1.2             # cuplaj intern (Kuramoto)
    K_ext: float = 1.5             # cuplaj catre estimarea umana
    beta_min: float = 0.20         # planseu minim (calibreaza cu calibration.py)
    rsi_window: int = 50           # fereastra medie mobila pt RSI
    omega_mean: float = 1.0
    omega_std: float = 0.05
    kalman_Q: tuple = (1e-4, 1e-3)   # zgomot proces [pozitie, viteza]
    kalman_R: float = 0.05           # zgomot presupus al proxy-ului
    seed: int | None = None


class KalmanHumanEstimator:
    """Filtru Kalman pentru estimarea (theta_uman, omega_uman) dintr-un
    proxy zgomotos. ATENTIE: daca R nu reflecta zgomotul REAL al proxy-ului,
    incertitudinea proprie a filtrului (P) nu va reflecta realitatea -
    vezi Sectiunea 25.4 a documentului REAI (variabila adaptiva testata
    si respinsa din acest motiv)."""

    def __init__(self, dt, Q, R, theta0=0.0, omega0=1.0):
        self.dt = dt
        self.F = np.array([[1, dt], [0, 1]])
        self.Q = np.diag(Q)
        self.H = np.array([[1.0, 0.0]])
        self.R = np.array([[max(R, 1e-6)]])
        self.x = np.array([theta0, omega0], dtype=float)
        self.P = np.eye(2) * 1.0

    def update(self, z):
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q
        y_resid = z - (self.H @ x_pred)[0]
        S = self.H @ P_pred @ self.H.T + self.R
        K_gain = P_pred @ self.H.T / S
        self.x = x_pred + (K_gain.flatten() * y_resid)
        self.P = (np.eye(2) - K_gain @ self.H) @ P_pred
        return self.x[0], self.x[1]  # theta_est, omega_est


class UKBEEngine:
    """Motorul de simulare complet: N oscilatori Kuramoto interni,
    cuplati dinamic (alpha/beta) cu o estimare Kalman a fazei umane."""

    def __init__(self, config: UKBEConfig):
        self.cfg = config
        rng = np.random.default_rng(config.seed)
        self.omega_i = rng.normal(config.omega_mean, config.omega_std, config.N)
        self.theta_i = rng.uniform(0, 2 * np.pi, config.N)
        self.kalman = KalmanHumanEstimator(
            config.dt, config.kalman_Q, config.kalman_R,
            theta0=0.0, omega0=config.omega_mean,
        )
        self.RSI = 0.1
        self._rsi_history = []
        self.t = 0.0
        # log pentru evenimente neasteptate (Sectiunea 12, pasul 8 din REAI)
        self.unexpected_events = []
        self._last_Phi = None

    def step(self, human_proxy_observation: float) -> dict:
        """Un pas de simulare. `human_proxy_observation` e valoarea
        zgomotoasa observata a fazei umane (proxy, cf Problema P1)."""
        cfg = self.cfg
        self.t += cfg.dt

        theta_human_est, _ = self.kalman.update(human_proxy_observation)

        beta = max(1 - self.RSI, cfg.beta_min)
        alpha = 1 - beta

        phase_diff = self.theta_i[None, :] - self.theta_i[:, None]
        kuramoto_term = (cfg.K_int / cfg.N) * np.sin(phase_diff).sum(axis=1)
        ext_term = cfg.K_ext * np.sin(theta_human_est - self.theta_i)
        dtheta = self.omega_i + alpha * kuramoto_term + beta * ext_term
        self.theta_i = self.theta_i + cfg.dt * dtheta

        Phi_intern = np.abs(np.mean(np.exp(1j * self.theta_i)))
        theta_mean = np.angle(np.mean(np.exp(1j * self.theta_i)))
        # psi infasurat corect (Sectiunea 26.3 - bug de infasurare gasit si corectat)
        psi = np.angle(np.exp(1j * (theta_mean - theta_human_est)))
        Phi_extern = (1 + np.cos(psi)) / 2.0   # formula corectata (Sectiunea 25.1)

        Phi_t = alpha * Phi_intern + beta * Phi_extern
        self._rsi_history.append(Phi_t)
        if len(self._rsi_history) > cfg.rsi_window:
            self._rsi_history = self._rsi_history[-cfg.rsi_window:]
        self.RSI = float(np.mean(self._rsi_history))

        if self._last_Phi is not None and abs(Phi_t - self._last_Phi) > 0.3:
            self.unexpected_events.append((self.t, Phi_t))
        self._last_Phi = Phi_t

        return {
            "t": self.t,
            "RSI": self.RSI,
            "Phi_intern": float(Phi_intern),
            "Phi_extern": float(Phi_extern),
            "psi": float(psi),
            "alpha": float(alpha),
            "beta": float(beta),
            "theta_human_est": float(theta_human_est),
        }

    def run(self, human_proxy_series) -> list[dict]:
        return [self.step(z) for z in human_proxy_series]

    def get_state_snapshot(self) -> dict:
        """Starea curenta completa a motorului - folosita pentru Entropy Valve
        check si pentru inregistrarea de stare la notarizare (Sectiunea DataCore).
        H = 1 - Phi_intern (entropie ca lipsa de coerenta interna)."""
        Phi_intern = float(np.abs(np.mean(np.exp(1j * self.theta_i))))
        H = 1.0 - Phi_intern
        theta_mean = np.angle(np.mean(np.exp(1j * self.theta_i)))
        # lock_ratio: fractia de oscilatori interni in +/- 0.3 rad fata de medie
        phase_dev = np.abs(np.angle(np.exp(1j * (self.theta_i - theta_mean))))
        lock_ratio = float(np.mean(phase_dev < 0.3))
        return {
            "t": self.t,
            "phi_intern": Phi_intern,
            "h": H,
            "rsi": self.RSI,
            "theta": self.theta_i.tolist(),
            "theta_mean": float(theta_mean),
            "lock_ratio": lock_ratio,
            "n_unexpected_events": len(self.unexpected_events),
        }
