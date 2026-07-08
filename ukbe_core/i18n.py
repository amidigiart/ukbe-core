"""
i18n.py - Internationalizare minimala pentru mesajele motorului UKBE
(evenimente de log, mesaje de eroare, recomandari).

Nu e un framework complex - e un catalog de mesaje cu interpolare,
suficient pentru mesajele tehnice generate de acest pachet. Pentru
UI-uri complete, foloseste un framework i18n complet (Babel, gettext).
"""
from __future__ import annotations

_CATALOG = {
    "ro": {
        "beta_min_below_threshold": "beta_min ({beta_min:.3f}) e sub pragul de bifurcatie "
                                     "({threshold:.3f}) - sistemul NU se va bloca de faza.",
        "beta_min_ok": "beta_min ({beta_min:.3f}) respecta marja de siguranta fata de prag "
                       "({threshold:.3f}).",
        "signature_invalid": "Semnatura nu e valida pentru continutul si cheia data.",
        "content_tampered": "Continutul a fost alterat dupa semnare - hash-ul nu se potriveste.",
    },
    "en": {
        "beta_min_below_threshold": "beta_min ({beta_min:.3f}) is below the bifurcation "
                                     "threshold ({threshold:.3f}) - the system will NOT phase-lock.",
        "beta_min_ok": "beta_min ({beta_min:.3f}) respects the safety margin over the "
                       "threshold ({threshold:.3f}).",
        "signature_invalid": "Signature is not valid for the given content and key.",
        "content_tampered": "Content was altered after signing - hash does not match.",
    },
}

_DEFAULT_LOCALE = "en"


def translate(key: str, locale: str = _DEFAULT_LOCALE, **kwargs) -> str:
    catalog = _CATALOG.get(locale, _CATALOG[_DEFAULT_LOCALE])
    template = catalog.get(key)
    if template is None:
        # fallback explicit, nu ascunde lipsa traducerii
        return f"[missing translation: {key}]"
    return template.format(**kwargs)


def available_locales() -> list[str]:
    return list(_CATALOG.keys())
