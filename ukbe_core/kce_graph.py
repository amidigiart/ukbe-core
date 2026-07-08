"""
kce_graph.py - Prototip pentru Knowledge Continuity Engineering (KCE),
Sectiunea 19 din documentul REAI, acum cu implementare reala.

IDEEA (validata azi ca merita prototipata, respinsa initial ca "Graph RAG
decentralizat" vag): decupleaza memoria/valorile sistemului de greutatile
oricarui model AI curent. Modelele vin si pleaca; graful de cunostinte,
semnat criptografic, ramane - verificabil independent de care model
"citeste" din el la un moment dat.

CE ESTE, concret:
- Un graf DIRECT ACICLIC (DAG) de noduri de cunoastere, append-only (nu se
  modifica niciodata un nod existent - doar se adauga noduri noi, care pot
  face referire la parinti)
- Fiecare nod e semnat (Ed25519, din notary.py, deja testat) - oricine
  poate verifica independent ca un nod n-a fost alterat
- Doua categorii de noduri, cu guvernanta DIFERITA:
  * "fact"  - cunoastere obisnuita, o singura semnatura e suficienta
  * "axiom" - valori centrale/reguli axiologice, necesita semnaturi de la
    TOTI custozii desemnati (multi-sig) - niciun custode singur nu poate
    schimba unilateral "sufletul" sistemului

CE NU ESTE, spus direct:
- NU e "Retrieval-Augmented Generation" real - nu exista niciun model de
  embeddings aici, nicio cautare semantica. Cautarea e pe etichete (tags),
  simpla, testabila, dar NU "intelege" continutul. Un RAG real ar avea
  nevoie de un model de embeddings testat separat - nu inventat aici doar
  ca sa completeze acronimul.
- NU rezolva Problema P1 (daca "axiomele" scrise reflecta corect intentia
  umana reala) - doar garanteaza ca, odata scrise si semnate, nu pot fi
  alterate tacit de un singur actor.
"""
from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature


def canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass
class KnowledgeNode:
    id: str
    node_type: str  # "fact" sau "axiom"
    content: str
    tags: list[str]
    created_at: str
    parent_ids: list[str]
    signatures: list[dict] = field(default_factory=list)  # [{"signer_id", "public_key_hex", "signature_hex"}]

    def _signable_payload(self) -> dict:
        """Ce anume se semneaza - totul in afara de lista de semnaturi
        insasi (evident, altfel semnatura s-ar auto-referi)."""
        return {
            "id": self.id, "node_type": self.node_type, "content": self.content,
            "tags": sorted(self.tags), "created_at": self.created_at,
            "parent_ids": sorted(self.parent_ids),
        }

    def content_hash(self) -> str:
        return hashlib.sha256(canonical_json(self._signable_payload())).hexdigest()


class GovernanceError(ValueError):
    """Ridicata cand un nod de tip 'axiom' nu are semnaturile tuturor
    custozilor desemnati."""
    pass


class IntegrityError(ValueError):
    """Ridicata cand un nod nu trece verificarea de semnatura/lineage."""
    pass


class KCEGraph:
    def __init__(self, axiom_custodian_pubkeys: dict[str, bytes]):
        """
        axiom_custodian_pubkeys: {signer_id: public_key_bytes} - TOTI acesti
        custozi trebuie sa semneze orice nod de tip 'axiom' pentru ca acesta
        sa fie acceptat in graf. Pentru noduri 'fact', e suficienta o
        singura semnatura de la oricine.
        """
        self.nodes: dict[str, KnowledgeNode] = {}
        self.axiom_custodian_pubkeys = dict(axiom_custodian_pubkeys)

    def add_fact(self, node_id: str, content: str, tags: list[str],
                 parent_ids: list[str], signer_id: str,
                 private_key: bytes, public_key: bytes) -> KnowledgeNode:
        node = KnowledgeNode(
            id=node_id, node_type="fact", content=content, tags=tags,
            created_at=datetime.now(timezone.utc).isoformat(), parent_ids=parent_ids,
        )
        self._verify_parents_exist(parent_ids)
        priv = Ed25519PrivateKey.from_private_bytes(private_key)
        sig = priv.sign(node.content_hash().encode("utf-8"))
        node.signatures.append({
            "signer_id": signer_id, "public_key_hex": public_key.hex(), "signature_hex": sig.hex(),
        })
        self.nodes[node_id] = node
        return node

    def add_axiom(self, node_id: str, content: str, tags: list[str],
                   parent_ids: list[str],
                   custodian_signatures: dict[str, tuple[bytes, bytes]]) -> KnowledgeNode:
        """custodian_signatures: {signer_id: (private_key, public_key)} - TREBUIE
        sa contina exact toti custozii din self.axiom_custodian_pubkeys, nici
        unul mai putin. Arunca GovernanceError daca lipseste vreunul."""
        missing = set(self.axiom_custodian_pubkeys) - set(custodian_signatures)
        if missing:
            raise GovernanceError(
                f"Nod axiom respins - lipsesc semnaturile custozilor: {sorted(missing)}"
            )

        self._verify_parents_exist(parent_ids)
        node = KnowledgeNode(
            id=node_id, node_type="axiom", content=content, tags=tags,
            created_at=datetime.now(timezone.utc).isoformat(), parent_ids=parent_ids,
        )
        payload_hash = node.content_hash().encode("utf-8")

        for signer_id, (private_key, public_key) in custodian_signatures.items():
            priv = Ed25519PrivateKey.from_private_bytes(private_key)
            sig = priv.sign(payload_hash)
            node.signatures.append({
                "signer_id": signer_id, "public_key_hex": public_key.hex(), "signature_hex": sig.hex(),
            })

        self.nodes[node_id] = node
        return node

    def _verify_parents_exist(self, parent_ids: list[str]) -> None:
        missing = [pid for pid in parent_ids if pid not in self.nodes]
        if missing:
            raise ValueError(f"Parinti inexistenti in graf: {missing}")

    def verify_node(self, node_id: str) -> bool:
        """Verifica DOAR acest nod - toate semnaturile lui sunt valide,
        si (daca e axiom) ca toti custozii ceruti au semnat."""
        node = self.nodes[node_id]
        payload_hash = node.content_hash().encode("utf-8")

        for sig_entry in node.signatures:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig_entry["public_key_hex"]))
            try:
                pub.verify(bytes.fromhex(sig_entry["signature_hex"]), payload_hash)
            except InvalidSignature:
                return False

        if node.node_type == "axiom":
            signed_by = {s["signer_id"] for s in node.signatures}
            if set(self.axiom_custodian_pubkeys) - signed_by:
                return False  # lipseste vreun custode - nu (mai) e valid guvernat

        return True

    def verify_lineage(self, node_id: str) -> bool:
        """Verifica NODUL si TOTI stramosii lui, recursiv. Un singur nod
        alterat oriunde in lant invalideaza intregul lant descendent."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        if not self.verify_node(node_id):
            return False
        return all(self.verify_lineage(pid) for pid in node.parent_ids)

    def query_by_tag(self, tag: str) -> list[KnowledgeNode]:
        """Cautare pe etichete - NU semantica. Vezi onestitatea din capul
        fisierului: nu exista niciun model de embeddings aici."""
        return [n for n in self.nodes.values() if tag in n.tags]

    def export_signed_snapshot(self) -> dict:
        """Exporta tot graful ca dict serializabil - pentru transfer catre
        un model AI nou, sau pentru arhivare externa (Sectiunea 19 din REAI:
        continuitatea trebuie sa supravietuiasca schimbarii de model)."""
        return {
            "format": "kce-graph-snapshot",
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "axiom_custodians": {k: v.hex() for k, v in self.axiom_custodian_pubkeys.items()},
            "nodes": {
                nid: {
                    "id": n.id, "node_type": n.node_type, "content": n.content,
                    "tags": n.tags, "created_at": n.created_at, "parent_ids": n.parent_ids,
                    "signatures": n.signatures,
                }
                for nid, n in self.nodes.items()
            },
        }
