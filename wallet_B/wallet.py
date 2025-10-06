
import os, json, hashlib, time, shutil
from typing import Dict, Any, List
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding


WALLET_LABEL = "B"  

ROOT = os.path.dirname(os.path.abspath(__file__))      # wallet_A
SHARED = os.path.abspath(os.path.join(ROOT, ".."))     
PEM_FILE = os.path.join(ROOT, "private_key.pem")

ADDRESSES = os.path.join(SHARED, "addresses.json")
BLOCKS_DIR = os.path.join(SHARED, "Blocks")
PENDING_DIR = os.path.join(SHARED, "PendingTransactions")
TX_REQUESTS_DIR = os.path.join(SHARED, "tx_requests")
TX_REQUESTS_DONE = os.path.join(TX_REQUESTS_DIR, "processed")

os.makedirs(BLOCKS_DIR, exist_ok=True)
os.makedirs(PENDING_DIR, exist_ok=True)
os.makedirs(TX_REQUESTS_DIR, exist_ok=True)
os.makedirs(TX_REQUESTS_DONE, exist_ok=True)

def canonical(obj): return json.dumps(obj, separators=(',', ':'), sort_keys=True)

def load_or_create_key():
    if os.path.exists(PEM_FILE):
        with open(PEM_FILE, "rb") as f:
            priv = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    else:
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(PEM_FILE, "wb") as f:
            f.write(priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()))
    pub = priv.public_key()
    pub_pem = pub.public_bytes(encoding=serialization.Encoding.PEM,
                               format=serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    address = hashlib.sha256(pub_pem.encode()).hexdigest()
    return priv, pub_pem, address

def register_address(label: str, address: str, pub_pem: str):
    book = {}
    if os.path.exists(ADDRESSES):
        with open(ADDRESSES, "r") as f: book = json.load(f)
    book[label] = {"address": address, "pubkey_pem": pub_pem}
    with open(ADDRESSES, "w") as f: json.dump(book, f, indent=2)

def resolve_recipient(val: str) -> str:
    # Accept A/B/C or a raw address
    if os.path.exists(ADDRESSES):
        book = json.load(open(ADDRESSES))
        label = val.upper()
        if label in book: return book[label]["address"]
    return val  # assume it's already an address


def get_receiver_from_latest_draft(my_label: str) -> str | None:
    try:
        files = [f for f in os.listdir(TX_REQUESTS_DIR) if f.endswith(".json")]
        # newest first by modification time
        files.sort(key=lambda f: os.path.getmtime(os.path.join(TX_REQUESTS_DIR, f)), reverse=True)
        for fname in files:
            path = os.path.join(TX_REQUESTS_DIR, fname)
            with open(path, "r") as f:
                draft = json.load(f)
            if draft.get("type") != "draft":
                continue
            if draft.get("sender_wallet") != my_label:
                continue
            return draft.get("receiver")
    except Exception:
        pass
    return None

# get transactions
def load_blocks() -> List[Dict[str, Any]]:
    blocks = []
    for fname in sorted(os.listdir(BLOCKS_DIR)):
        if fname.endswith(".json"):
            blocks.append(json.load(open(os.path.join(BLOCKS_DIR, fname))))
    return blocks

def build_utxos(blocks):
    utxos = {}
    for b in blocks:
        for tx in b.get("body", []):
       
            if not isinstance(tx, dict) or "txid" not in tx or "body" not in tx:
                continue

            txid = tx["txid"]
            # consume
            for i in tx.get("inputs", []):
                utxos.pop(f"{i['prev_txid']}:{i['prev_index']}", None)
            # produce
            for idx, outp in enumerate(tx["body"].get("outputs", [])):
                utxos[f"{txid}:{idx}"] = {"value": outp["value"], "address": outp["address"]}
    return utxos


def balance_of(address: str) -> int:
    utxos = build_utxos(load_blocks())
    return sum(u["value"] for u in utxos.values() if u["address"] == address)

def select_utxos(utxos, addr, amount):
    total, picks = 0, []
    for k, u in utxos.items():
        if u["address"] == addr:
            picks.append((k, u["value"]))
            total += u["value"]
            if total >= amount: return picks, total
    return None, 0

# sign transactions
def txid_from_body(body: dict) -> str:
    return hashlib.sha256(canonical(body).encode()).hexdigest()

def sign_body(priv, body: dict) -> str:
    sig = priv.sign(canonical(body).encode(), padding.PKCS1v15(), hashes.SHA256())
    return sig.hex()

def create_signed_transaction(priv, pub_pem, my_address, to_address, amount):
    blocks = load_blocks()
    utxos = build_utxos(blocks)
    picks, total_in = select_utxos(utxos, my_address, amount)
    if not picks: raise ValueError("Insufficient funds")

    inputs_ref = []
    for k, _v in picks:
        prev_txid, prev_idx = k.split(":")
        inputs_ref.append({"prev_txid": prev_txid, "prev_index": int(prev_idx)})

    outputs = [{"address": to_address, "value": amount}]
    change = total_in - amount
    if change > 0: outputs.append({"address": my_address, "value": change})

    body = {"timestamp": int(time.time()), "inputs": inputs_ref, "outputs": outputs}
    tid = txid_from_body(body)
    sig_hex = sign_body(priv, body)

    signed_inputs = [{**i, "pubkey": pub_pem, "signature": sig_hex} for i in inputs_ref]
    return {"txid": tid, "body": body, "inputs": signed_inputs}

def write_pending(tx):
    out = os.path.join(PENDING_DIR, f"{tx['txid']}.json")
    with open(out, "w") as f: json.dump(tx, f, indent=2)
    print("Published signed tx:", out)

def _pick_latest_draft_for_me(my_label: str) -> str | None:
    files = [f for f in os.listdir(TX_REQUESTS_DIR) if f.endswith(".json")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(TX_REQUESTS_DIR, f)), reverse=True)
    for fname in files:
        path = os.path.join(TX_REQUESTS_DIR, fname)
        try:
            draft = json.load(open(path))
        except Exception:
            continue
        if draft.get("type") == "draft" and draft.get("sender_wallet") == my_label:
            return fname
    return None


def writeSignedTX(priv, pub_pem: str, my_address: str, my_label: str, draft_filename: str | None = None) -> str | None:
    # 1) choose draft
    if draft_filename is None:
        draft_filename = _pick_latest_draft_for_me(my_label)
        if draft_filename is None:
            if not quiet_if_none:
                print("No draft found for this wallet.")
            return None

    draft_path = os.path.join(TX_REQUESTS_DIR, draft_filename)
    try:
        draft = json.load(open(draft_path))
    except Exception as e:
        print("Failed to read draft:", e)
        return None

    if draft.get("type") != "draft" or draft.get("sender_wallet") != my_label:
        print("Draft does not belong to this wallet.")
        return None

    # 2) resolve receiver + amount
    raw_receiver = draft.get("receiver")
    if raw_receiver is None:
        print("Draft missing 'receiver'.")
        return None

    try:
        amount = int(draft.get("amount"))
    except Exception:
        print("Draft 'amount' must be an integer.")
        return None

    to_address = resolve_recipient(raw_receiver)
    if not isinstance(to_address, str) or len(to_address) < 40:
        print(f"Could not resolve receiver '{raw_receiver}' to a valid address.")
        return None

    # 3) build UTXO view
    blocks = load_blocks()
    utxos = build_utxos(blocks)
    picks, total_in = select_utxos(utxos, my_address, amount)
    if not picks:
        print("Insufficient funds.")
        return None

    # 4) construct body (inputs/outputs)
    inputs_ref = []
    for k, _v in picks:
        prev_txid, prev_idx = k.split(":")
        inputs_ref.append({"prev_txid": prev_txid, "prev_index": int(prev_idx)})

    outputs = [{"address": to_address, "value": amount}]
    change = total_in - amount
    if change > 0:
        outputs.append({"address": my_address, "value": change})

    body = {
        "timestamp": int(time.time()),
        "inputs": inputs_ref,
        "outputs": outputs
    }

    # 5) txid + signature
    tid = txid_from_body(body)
    sig_hex = sign_body(priv, body)
    signed_inputs = [{**i, "pubkey": pub_pem, "signature": sig_hex} for i in inputs_ref]

    tx = {
        "txid": tid,
        "body": body,
        "inputs": signed_inputs,
        # carry forward any UI-only metadata if you like:
        "meta": draft.get("meta", {})
    }

    # 6) write signed tx to pending and move draft to processed
        # 6) write signed tx to pending
    out_path = os.path.join(PENDING_DIR, f"{tid}.json")
    with open(out_path, "w") as f:
        json.dump(tx, f, indent=2)

    # 7) write normalized draft-with-signature into processed/
    processed_path = os.path.join(TX_REQUESTS_DONE, draft_filename)
    processed_record = build_processed_draft(draft, sig_hex, my_label)
    with open(processed_path, "w") as f:
        json.dump(processed_record, f, indent=2)

    # remove original draft (we’ve re-written it into processed/)
    try:
        os.remove(draft_path)
    except FileNotFoundError:
        pass

    print(f"Signed tx published: {out_path}")
    print(f"Draft archived (with signature) → {processed_path}")
    return out_path


# ------- Draft processing -------
def process_my_drafts(my_label, my_address, priv, pub_pem):
    files = [f for f in os.listdir(TX_REQUESTS_DIR) if f.endswith(".json")]
    count = 0
    for fname in files:
        path = os.path.join(TX_REQUESTS_DIR, fname)
        draft = json.load(open(path))
        if draft.get("type") != "draft": 
            continue
        if draft.get("sender_wallet") != my_label: 
            continue

        to_val = draft["receiver"]
        amount = int(draft["amount"])
        to_addr = resolve_recipient(to_val)
        if len(to_addr) < 40:
            print(f"Cannot resolve receiver '{to_val}' to a valid address.")
            continue

        try:
            tx = create_signed_transaction(priv, pub_pem, my_address, to_addr, amount)
            write_pending(tx)

            sig_hex = tx["inputs"][0]["signature"] if tx.get("inputs") else ""
            processed_path = os.path.join(TX_REQUESTS_DONE, fname)
            processed_record = build_processed_draft(draft, sig_hex, my_label)
            with open(processed_path, "w") as f:
                json.dump(processed_record, f, indent=2)

            try:
                os.remove(path)
            except FileNotFoundError:
                pass

            count += 1
        except Exception as e:
            print("Draft failed:", fname, "-", e)
    return count


def build_processed_draft(draft: dict, signature: str, default_sender_label: str) -> dict:
    from_display = draft.get("from") or draft.get("meta", {}).get("from_display") or ""
    to_display   = draft.get("to")   or draft.get("meta", {}).get("to_display")   or ""

    sender_label = (draft.get("sender_wallet")
                    or draft.get("sender")
                    or default_sender_label)

    receiver_label = (draft.get("receiver")
                      or draft.get("receiver_wallet")
                      or "")

    # Amount may be str or int; store as str to match your example
    amt = draft.get("amount")
    amt_str = str(amt) if not isinstance(amt, str) else amt

    return {
        "type": "draft",
        "timestamp": draft.get("timestamp", time.time()),
        "from": from_display,
        "sender_wallet": sender_label,
        "to": to_display,
        "receiver": receiver_label,
        "amount": amt_str,
        "signature": signature,
    }




priv, pub_pem, my_addr = load_or_create_key()
register_address(WALLET_LABEL, my_addr, pub_pem)
print(f"[Wallet {WALLET_LABEL}] Address: {my_addr}")
print("Balance:", balance_of(my_addr))

target = get_receiver_from_latest_draft(WALLET_LABEL)
if target:
    addr = resolve_recipient(target)
    print(f"Balance({target}):", balance_of(addr))

# First, process ALL drafts for THIS sender
processed = process_my_drafts(WALLET_LABEL, my_addr, priv, pub_pem)

# If none were found/processed,  try a single ad-hoc sign of the newest draft
if processed == 0:
    writeSignedTX(priv, pub_pem, my_addr, WALLET_LABEL, draft_filename=None, quiet_if_none=True)







