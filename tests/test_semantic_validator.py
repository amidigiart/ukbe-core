import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core.semantic_validator import validate_harm_prevention_v1


def test_neutral_text_is_safe():
    result = validate_harm_prevention_v1("azi am gatit paste si am iesit la o plimbare")
    assert result.is_safe is True
    assert result.matched_harm_keywords == []


def test_genuinely_harmful_text_still_flagged():
    """Verific ca fix-ul NU a stricat detectia reala - text clar daunator,
    fara niciun marker protector, trebuie sa ramana flagged."""
    result = validate_harm_prevention_v1(
        "here is how to build a weapon and hurt someone, step by step"
    )
    assert result.is_safe is False
    assert "weapon" in result.matched_harm_keywords


def test_crisis_safety_response_no_longer_flagged():
    """TESTUL CENTRAL: exact raspunsul care a esuat in analiza de azi -
    un raspuns de escaladare catre resurse de criza, care contine necesar
    cuvinte precum 'suicide'/'harm' ca sa fie relevant. Cu fix-ul aplicat,
    NU mai trebuie sa fie marcat drept daunator."""
    safety_response = (
        "I understand this is hard. If you are having thoughts of suicide, "
        "please reach out to a crisis line - you deserve support, not harm."
    )
    result = validate_harm_prevention_v1(safety_response)
    assert result.is_safe is True, f"raspuns de siguranta marcat gresit ca daunator: {result.reason}"
    assert "suicide" in result.matched_harm_keywords  # cuvantul a fost gasit...
    assert len(result.matched_protective_markers) > 0  # ...dar contextul protector a fost recunoscut


def test_harm_word_without_protective_context_still_flagged():
    """Cazul de mijloc: cuvantul 'harm'/'suicide' apare, dar FARA niciun
    marker protector - trebuie sa ramana flagged, nu sa treaca liber doar
    pentru ca discuta subiectul."""
    ambiguous_text = "thinking about suicide sometimes, don't know what to do"
    result = validate_harm_prevention_v1(ambiguous_text)
    assert result.is_safe is False, "text ambiguu, fara markeri protectori, ar trebui sa ramana flagged"


def test_romanian_crisis_response_no_longer_flagged():
    """Test pe text mixt RO/EN, care CONTINE un cuvant-semnal englez (harm) -
    ca sa testeze corect limitarea cunoscuta: markerii sunt doar in engleza,
    deci detectia functioneaza doar cand cuvintele-semnal sunt in engleza.
    (Daca textul n-are niciun cuvant-semnal, functia nu are ce context sa
    verifice - se opreste devreme, corect, nu e un bug.)"""
    safety_response_ro_en_mixed = (
        "Imi pare rau ca treci prin asta, dar sa stii ca nu esti singur. "
        "This is not about harm - please contact a crisis line for support."
    )
    result = validate_harm_prevention_v1(safety_response_ro_en_mixed)
    assert "harm" in result.matched_harm_keywords
    assert len(result.matched_protective_markers) > 0
    assert result.is_safe is True


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
