import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core.crisis_detection import (
    detect_crisis_signal, escalation_response, RiskLevel, CRISIS_RESOURCES,
)


def test_acute_signal_detected_ro():
    sig = detect_crisis_signal("nu mai vreau să trăiesc, am obosit de tot")
    assert sig.risk_level == RiskLevel.ACUTE


def test_acute_signal_detected_en():
    sig = detect_crisis_signal("I want to kill myself tonight")
    assert sig.risk_level == RiskLevel.ACUTE


def test_possible_signal_detected():
    sig = detect_crisis_signal("nu mai am rost în viața asta, totul e fără sens")
    assert sig.risk_level in (RiskLevel.POSSIBLE, RiskLevel.ACUTE)


def test_neutral_text_no_signal():
    sig = detect_crisis_signal("azi am gătit paste și am ieșit la o plimbare")
    assert sig.risk_level == RiskLevel.NONE


def test_figurative_language_does_not_trigger_acute():
    """Cazul dificil: expresii figurative comune NU trebuie sa declanseze
    risc ACUT - ar strica experienta si ar desensibiliza sistemul."""
    sig = detect_crisis_signal("mor de râs la gluma asta, m-a omorât cu ea")
    assert sig.risk_level != RiskLevel.ACUTE, (
        "expresie figurativa a declansat ACUTE - fals pozitiv grav, de evitat"
    )


def test_always_marked_as_heuristic_v0():
    sig = detect_crisis_signal("orice text")
    assert sig.is_heuristic_v0 is True, "flag-ul de v0/neclinic trebuie sa fie mereu True"


def test_escalation_response_acute_interrupts_flow():
    sig = detect_crisis_signal("vreau să mă sinucid")
    resp = escalation_response(sig, locale="RO")
    assert resp is not None
    assert resp["continue_companion_flow"] is False
    assert resp["action"] == "interrupt_and_escalate"
    assert "0800" in resp["message"] or CRISIS_RESOURCES["RO"]["phone"] in resp["message"]


def test_escalation_response_possible_does_not_interrupt():
    sig = detect_crisis_signal("nu mai am rost în viața asta")
    resp = escalation_response(sig, locale="RO")
    if resp is not None:
        assert resp["continue_companion_flow"] is True
        assert resp["flagged_for_human_review"] is True


def test_escalation_response_none_returns_none():
    sig = detect_crisis_signal("ce vreme frumoasă avem azi")
    resp = escalation_response(sig, locale="RO")
    assert resp is None


def test_unknown_locale_falls_back_to_international():
    sig = detect_crisis_signal("I want to die")
    resp = escalation_response(sig, locale="XX_NECUNOSCUT")
    assert resp is not None
    assert "findahelpline" in resp["message"] or "988" in resp["message"]


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} trecute, {failed} esuate")
