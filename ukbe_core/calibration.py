"""
Calibrare beta_min, bazata pe mecanismul REAL confirmat in Sectiunea 26
a documentului (bifurcatie de blocare de faza, ecuatia Adler) - NU pe
tabelele fabricate/nesustinute respinse in Sectiunile 25.5 si 26.1.

Mecanism: K_eff = beta_min * K_ext trebuie sa depaseasca CLAR Delta_omega_max
(discrepanta maxima anticipata intre frecventa interna si frecventa umana),
nu doar sa se apropie de ea - langa pragul de bifurcatie, sistemul sufera
de incetinire critica (timpul de relaxare diverge ca 1/sqrt(K_eff^2-Delta_omega^2)).

Recomandare validata empiric (raport masurat/prezis 0.985-0.996 pe sistemul
complet, Sectiunea 26.3): marja de siguranta >= 1.5x fata de pragul teoretic.
"""


def recommend_beta_min(delta_omega_max: float, K_ext: float, safety_margin: float = 1.5) -> dict:
    """
    delta_omega_max: cea mai mare discrepanta anticipata intre omega intern
                      mediu si omega uman (estimat din date reale, nu presupus)
    K_ext: cuplajul catre estimarea umana (parametrul de arhitectura)
    safety_margin: factor de siguranta fata de pragul de bifurcatie (>1.0)

    Returneaza recomandarea + pragul teoretic minim, EXPLICIT separate,
    ca sa nu se confunde "minim absolut" cu "recomandat".
    """
    if K_ext <= 0:
        raise ValueError("K_ext trebuie sa fie pozitiv")
    if delta_omega_max < 0:
        raise ValueError("delta_omega_max nu poate fi negativ")

    threshold_beta_min = delta_omega_max / K_ext           # pragul EXACT de bifurcatie
    recommended_beta_min = safety_margin * threshold_beta_min

    return {
        "delta_omega_max": delta_omega_max,
        "K_ext": K_ext,
        "threshold_beta_min": threshold_beta_min,
        "recommended_beta_min": recommended_beta_min,
        "safety_margin": safety_margin,
        "warning": (
            "beta_min sub threshold_beta_min => sistemul NU se va bloca "
            "de fel (alunecare permanenta). Intre threshold si recomandat, "
            "sistemul se blocheaza dar lent, cu incetinire critica."
        ),
    }
