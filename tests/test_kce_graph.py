import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ukbe_core.kce_graph import KCEGraph, GovernanceError
from ukbe_core.notary import generate_keypair


def _make_custodians(n=3):
    custodians = {}
    for i in range(n):
        priv, pub = generate_keypair()
        custodians[f"custodian_{i}"] = (priv, pub)
    return custodians


def test_fact_node_single_signature_ok():
    custodians = _make_custodians()
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})

    priv, pub = generate_keypair()
    node = graph.add_fact("fact1", "Motorul UKBE foloseste ecuatia Adler", ["ukbe", "math"], [], "someone", priv, pub)

    assert graph.verify_node("fact1") is True


def test_axiom_requires_all_custodians():
    """TEST CENTRAL: un nod axiom FARA toti custozii trebuie respins la scriere."""
    custodians = _make_custodians(3)
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})

    incomplete_signers = dict(list(custodians.items())[:2])  # doar 2 din 3

    try:
        graph.add_axiom("axiom1", "Nu construim fara teste reale", ["values"], [], incomplete_signers)
        assert False, "ar fi trebuit sa respinga - lipseste un custode"
    except GovernanceError as e:
        assert "custodian_2" in str(e)


def test_axiom_with_all_custodians_succeeds():
    custodians = _make_custodians(3)
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})

    node = graph.add_axiom("axiom1", "Nu construim fara teste reale", ["values"], [], custodians)
    assert graph.verify_node("axiom1") is True
    assert len(node.signatures) == 3


def test_tampered_node_fails_verification():
    custodians = _make_custodians()
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})
    priv, pub = generate_keypair()
    graph.add_fact("fact1", "continut original", ["x"], [], "someone", priv, pub)

    graph.nodes["fact1"].content = "continut alterat dupa semnare"
    assert graph.verify_node("fact1") is False


def test_lineage_verification_walks_up_parents():
    custodians = _make_custodians()
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})
    priv, pub = generate_keypair()

    graph.add_fact("root", "cunostinta initiala", ["base"], [], "a", priv, pub)
    graph.add_fact("child", "extindere", ["base"], ["root"], "a", priv, pub)
    graph.add_fact("grandchild", "extindere mai departe", ["base"], ["child"], "a", priv, pub)

    assert graph.verify_lineage("grandchild") is True


def test_tampering_ancestor_invalidates_descendant_lineage():
    """Un stramos alterat trebuie sa invalideze verificarea lineage-ului
    pentru toti descendentii lui, chiar daca descendentii insisi n-au fost
    modificati."""
    custodians = _make_custodians()
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})
    priv, pub = generate_keypair()

    graph.add_fact("root", "cunostinta initiala", ["base"], [], "a", priv, pub)
    graph.add_fact("child", "extindere", ["base"], ["root"], "a", priv, pub)

    assert graph.verify_lineage("child") is True  # inainte de alterare

    graph.nodes["root"].content = "ALTERAT"
    assert graph.verify_lineage("child") is False, "stramos alterat trebuie sa strice lineage-ul descendentului"
    assert graph.verify_node("child") is True, "nodul copil insusi ramane valid izolat - doar lineage-ul e stricat"


def test_query_by_tag_is_literal_not_semantic():
    custodians = _make_custodians()
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})
    priv, pub = generate_keypair()

    graph.add_fact("f1", "despre pisici", ["animale"], [], "a", priv, pub)
    graph.add_fact("f2", "despre caini, care sunt tot animale", ["mamifere"], [], "a", priv, pub)

    results_animale = graph.query_by_tag("animale")
    assert len(results_animale) == 1  # DOAR f1 - f2 nu are tag-ul exact "animale", desi contine cuvantul in text
    assert results_animale[0].id == "f1"


def test_export_snapshot_contains_all_nodes_and_custodians():
    custodians = _make_custodians(2)
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})
    priv, pub = generate_keypair()
    graph.add_fact("f1", "test", ["t"], [], "a", priv, pub)

    snapshot = graph.export_signed_snapshot()
    assert snapshot["format"] == "kce-graph-snapshot"
    assert "f1" in snapshot["nodes"]
    assert len(snapshot["axiom_custodians"]) == 2


def test_missing_parent_rejected():
    custodians = _make_custodians()
    graph = KCEGraph({cid: pub for cid, (priv, pub) in custodians.items()})
    priv, pub = generate_keypair()

    try:
        graph.add_fact("orphan", "test", ["t"], ["nonexistent_parent"], "a", priv, pub)
        assert False, "ar fi trebuit sa respinga - parintele nu exista"
    except ValueError:
        pass


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
