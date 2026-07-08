"""
tezos_anchor.py - Ancorarea unui hash de notarizare pe blockchain-ul Tezos.

=====================================================================
STATUS: COD SCRIS, NETESTAT LIVE. Nu a fost verificat impotriva unei
retele Tezos reale in aceasta sesiune - mediul de dezvoltare nu are
acces la niciun nod RPC Tezos (lista de domenii permise nu il include).

INAINTE SA FOLOSESTI ASTA IN PRODUCTIE:
1. Testeaza intai pe Ghostnet (testnet-ul Tezos), NU pe mainnet.
2. Obtine XTZ de test gratuit de la un "faucet" Ghostnet (cauta
   "tezos ghostnet faucet" - adresele se schimba, nu le hardcodez aici).
3. Verifica manual pe un explorator de bloc (ex. tzkt.io/ghostnet)
   ca operatia chiar a ajuns pe lant, cu hash-ul corect.
4. Doar dupa ce (1)-(3) merg constant, ia in calcul mainnet.
=====================================================================

Mecanism: pentru a ancora un hash pe Tezos, cel mai simplu si robust
mod (fara sa scrii un smart contract propriu) e sa apelezi un contract
generic de "timestamping" deja existent pe retea, sau sa-ti deployezi
propriul contract minimal (Michelson/SmartPy) care stocheaza hash-uri
intr-un big_map. Acest fisier ofera:
  (a) template-ul de contract minimal (comentat, de deployat separat)
  (b) functia de apel, folosind libraria `pytezos`

Necesita: `pip install pytezos` (nu e inclusa implicit - dependinta grea,
cu legaturi native; instaleaz-o separat, nu vine cu ukbe_core).
"""

# --- (a) Template minimal de contract, in SmartPy-like pseudocod Michelson ---
# De deployat SEPARAT, o singura data, cu unealta ta preferata (SmartPy CLI,
# Taquito, sau pytezos). NU e deployat de codul de mai jos.
MINIMAL_ANCHOR_CONTRACT_TEMPLATE = """
# Contract minimal de ancorare hash-uri (concept, NU testat/deployat de noi)
# storage: big_map(string_hash -> timestamp)
# entrypoint "anchor": primeste un hash (string), il scrie in storage cu
# timestamp-ul blocului curent. Respinge daca hash-ul exista deja
# (imutabilitate - nu poate fi suprascris).
#
# Recomandare: foloseste un template deja auditat, nu scrie Michelson de
# la zero pentru productie. Cauta "tezos timestamping contract" pentru
# implementari existente si auditate.
"""


def anchor_hash_tezos(content_hash: str, contract_address: str,
                       rpc_url: str, private_key: str) -> dict:
    """
    Ancoreaza `content_hash` pe Tezos, apeland entrypoint-ul "anchor" al
    unui contract deja deployat la `contract_address`.

    NETESTAT LIVE. Structura apelului e corecta (pattern standard pytezos),
    dar nu a fost verificata impotriva unui nod real din acest mediu.

    Args:
        content_hash: hash-ul (hex) de ancorat - de la notary.py
        contract_address: adresa KT1... a contractului de ancorare, deja deployat
        rpc_url: URL-ul nodului RPC (ex. testnet Ghostnet pentru testare)
        private_key: cheia privata Tezos (format base58, incepe cu "edsk...")
                      - NU stoca asta in cod sursa; citeste din variabila de mediu

    Returns:
        dict cu hash-ul operatiei ("op_hash") si detalii, DACA reuseste.

    Raises:
        RuntimeError daca `pytezos` nu e instalat, sau daca apelul esueaza.
    """
    try:
        from pytezos import pytezos as pytezos_client
    except ImportError as e:
        raise RuntimeError(
            "Biblioteca 'pytezos' nu e instalata. Ruleaza `pip install pytezos` "
            "separat - e o dependinta grea (compilare nativa), de-asta nu e "
            "inclusa implicit in ukbe_core."
        ) from e

    client = pytezos_client.using(shell=rpc_url, key=private_key)
    contract = client.contract(contract_address)

    # apelul entrypoint-ului "anchor" - presupune ca semnatura contractului
    # accepta un singur parametru string (hash-ul). ADAPTEAZA la contractul
    # tau real - asta e un TEMPLATE, nu o interfata garantata.
    op = contract.anchor(content_hash).send(min_confirmations=1)

    return {
        "op_hash": op.hash(),
        "content_hash": content_hash,
        "contract_address": contract_address,
        "status": "trimis - verifica manual pe explorator ca a fost confirmat",
    }


def verify_anchor_tezos(content_hash: str, contract_address: str, rpc_url: str) -> dict:
    """
    Citeste storage-ul contractului si verifica daca `content_hash` a fost
    ancorat. NETESTAT LIVE - vezi avertismentul din capul fisierului.
    """
    try:
        from pytezos import pytezos as pytezos_client
    except ImportError as e:
        raise RuntimeError("Biblioteca 'pytezos' nu e instalata.") from e

    client = pytezos_client.using(shell=rpc_url)
    contract = client.contract(contract_address)
    storage = contract.storage()  # structura exacta depinde de contractul deployat

    found = content_hash in storage  # ADAPTEAZA la structura reala a storage-ului
    return {"content_hash": content_hash, "anchored": bool(found)}
