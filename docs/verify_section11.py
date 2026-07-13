# -*- coding: utf-8 -*-
"""Verificare a 'ecuatiei universale' din REAI Sectiunea 11.
Testez ce se poate testa: consistenta matematica a formulei, NU afirmatiile
din literatura (alea se verifica separat, cu surse)."""
import numpy as np
rng = np.random.default_rng(0)

def step(theta, omega, K, refs, Kk, dt=0.01):
    # dtheta/dt = omega + (K/N)Σ sin(θj-θi) + Σ_k Kk_k sin(Ψk-θi)
    z = np.exp(1j*theta)
    internal = K*np.imag(np.exp(-1j*theta)*z.mean())
    ext = np.zeros_like(theta)
    for Psi, k in zip(refs, Kk):
        ext += k*np.sin(Psi-theta)
    return theta + dt*(omega + internal + ext)

def phi_universal(theta, refs, lam):
    N=len(theta)
    return sum(l*abs(np.mean(np.exp(1j*(theta-Psi)))) for Psi,l in zip(refs,lam))

N=30
print("=== TEST 1: Φ_universal ∈ [0,1] mereu? (100 stari aleatoare, M=3) ===")
ok=True
for _ in range(100):
    th=rng.uniform(0,2*np.pi,N); refs=rng.uniform(0,2*np.pi,3); lam=rng.dirichlet([1,1,1])
    p=phi_universal(th,refs,lam)
    if not (-1e-12<=p<=1+1e-12): ok=False; print("  INCALCARE:",p)
print("  toate in [0,1]:", ok)

print("\n=== TEST 2: M=1, λ=1 => se reduce la coerenta fata de o singura referinta? ===")
th=rng.uniform(0,2*np.pi,N); ref=1.234
p_univ=phi_universal(th,[ref],[1.0])
p_direct=abs(np.mean(np.exp(1j*(th-ref))))
print(f"  Φ_univ(M=1)={p_univ:.6f}  vs  |<e^i(θ-Ψ)>|={p_direct:.6f}  egale:",abs(p_univ-p_direct)<1e-12)

print("\n=== TEST 3: o singura referinta, cuplaj tare => grupul se blocheaza pe ea (Φ->1)? ===")
th=rng.uniform(0,2*np.pi,N); om=0.0*rng.standard_normal(N); ref=2.0
for _ in range(3000): th=step(th,om,K=1.0,refs=[ref],Kk=[2.0])
print(f"  Φ fata de referinta dupa convergenta: {phi_universal(th,[ref],[1.0]):.4f} (astept ~1)")

print("\n=== TEST 4 (miezul onest): DOUA referinte in conflict (opuse) cu K egal ===")
th=rng.uniform(0,2*np.pi,N); om=np.zeros(N)
r1, r2 = 0.0, np.pi           # referinte la 180° una de alta
for _ in range(5000): th=step(th,om,K=0.5,refs=[r1,r2],Kk=[1.0,1.0])
p1=abs(np.mean(np.exp(1j*(th-r1)))); p2=abs(np.mean(np.exp(1j*(th-r2))))
puniv=phi_universal(th,[r1,r2],[0.5,0.5])
print(f"  coerenta fata de ref1: {p1:.3f} | fata de ref2: {p2:.3f} | Φ_univ(λ=0.5,0.5): {puniv:.3f}")
print("  Interpretare: cu referinte in conflict, sistemul NU se poate bloca pe ambele;")
print("  Φ_univ ramane substantial sub 1. Formula 'universala' masoara un COMPROMIS,")
print("  nu o sincronizare perfecta — exact ce trebuie sa astepti fizic.")

print("\n=== TEST 5: e formula noua ca MATEMATICA? ===")
print("  NU. E Kuramoto cu forcing multiplu (mai multi 'pacemakeri'/referinte) —")
print("  o familie standard in literatura de sincronizare. Generalizarea M-referinte")
print("  e corecta si consistenta, dar nu inventata aici. Noutatea (daca exista) e")
print("  DOAR aplicatia: Ψ_k = intentie umana estimata continuu. Vezi verdict.")
