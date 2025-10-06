import os
import json
import time
import hashlib
import shutil
from typing import List, Dict, Any
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


# block height counter
blockheight = 0

# transaction array
transactions = []
rejected_transactions = []
valdidated_transactions = []
valid_transactions = []


# per-iteration file lists
included_files = []
rejected_files = []


# block array
blocks = []

#load in directories to read transactions

#replace with where your path for the transaction directories
PENDING_DIR = "PendingTransactions"
PROCESSED_DIR = "ProcessedTransactions"
BLOCKS_DIR = "Blocks"

# Make sure directories exist
os.makedirs(PENDING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(BLOCKS_DIR, exist_ok=True)
# keep an 'invalid' bucket for rejects
os.makedirs(os.path.join(PROCESSED_DIR, "invalid"), exist_ok=True)

def canonical(obj) -> str:
    # stable, whitespace-free JSON
    return json.dumps(obj, separators=(',', ':'), sort_keys=True)

def merkle_root(txids: List[str]) -> str:
    if not txids:
        return hashlib.sha256(b'').hexdigest()
    layer = txids[:]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i] if i + 1 == len(layer) else layer[i + 1]
            nxt.append(hashlib.sha256((a + b).encode()).hexdigest())
        layer = nxt
    return layer[0]

def address_from_pub(pub_pem: str) -> str:
    # must match how wallet derives addresses
    return hashlib.sha256(pub_pem.encode()).hexdigest()

def verify_signature(pub_pem: str, data_bytes: bytes, sig_hex: str) -> bool:
    try:
        pub = serialization.load_pem_public_key(pub_pem.encode(), backend=default_backend())
        pub.verify(bytes.fromhex(sig_hex), data_bytes, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False

def list_block_files() -> List[str]:
    files = [f for f in os.listdir(BLOCKS_DIR) if f.endswith(".json")]
    files.sort()
    return files

def load_blocks() -> List[Dict[str, Any]]:
    chain = []
    for fname in list_block_files():
        path = os.path.join(BLOCKS_DIR, fname)
        try:
            with open(path, "r") as f:
                blk = json.load(f)
        except Exception:
            # unreadable -> skip
            continue

        header = blk.get("header")
        body   = blk.get("body")
        if not isinstance(header, dict) or not isinstance(body, list):
            # not a block-shaped JSON -> skip (legacy/project-1 or stray files)
            # print(f"[skip] non-block JSON in Blocks/: {fname}")
            continue

        # Optional: sanity check height
        if not isinstance(header.get("height"), int):
            # print(f"[skip] block without int height: {fname}")
            continue

        chain.append(blk)
    return chain




def build_utxos(blocks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    utxos = {}
    for b in blocks:
        for tx in b.get("body", []):
            if not isinstance(tx, dict) or "txid" not in tx or "body" not in tx:
                continue  # skip legacy entries
            txid = tx["txid"]
            for inp in tx.get("inputs", []):
                utxos.pop(f"{inp['prev_txid']}:{inp['prev_index']}", None)
            for i, outp in enumerate(tx["body"].get("outputs", [])):
                utxos[f"{txid}:{i}"] = {"value": outp["value"], "address": outp["address"]}
    return utxos


def process_pending_transactions():
    pending_files = os.listdir(PENDING_DIR)
    if not pending_files:
        print("No pending transactions to include in block.")
        return
        '''
    else:
      for filename in pending_files:
          with open(os.path.join(PENDING_DIR, filename), 'r') as f:
        content = json.load(f)
    transactions.append({ "hash": filename.replace(".json", ""),"content": content })
    '''

    chain = load_blocks()
    utxos = build_utxos(chain)
    #utxos = build_utxos(blocks)
    
    # Validate sequentially and update temp UTXO view so later txs in the same block can spend newly created outputs
    for fname in sorted(pending_files):
        path = os.path.join(PENDING_DIR, fname)
        try:
            with open(path, "r") as f:
                tx = json.load(f)
                #content = json.load(f)
                transactions.append(tx)
        except Exception:
            print(f"Rejected: {fname}")
            rejected_transaction.append(fname)
            rejected_files.append(fname)
            continue

        if validate_transaction(tx, utxos):
            valid_transactions.append(tx)
            valdidated_transactions.append(fname)
            included_files.append(fname)
            # apply to utxo view
            txid = tx["txid"]
            for inp in tx["inputs"]:
                utxos.pop(f"{inp['prev_txid']}:{inp['prev_index']}", None)
            for idx, outp in enumerate(tx["body"]["outputs"]):
                utxos[f"{txid}:{idx}"] = {"value": outp["value"], "address": outp["address"]}
        else:
            print(f"Rejected -> (invalid signature): {fname}")
            rejected_transactions.append(fname)
            rejected_files.append(fname)

    # Move rejected to processed/invalid
    for fname in rejected_transactions:
        shutil.move(os.path.join(PENDING_DIR, fname),
                    os.path.join(PROCESSED_DIR, "invalid", fname))

    if not valid_transactions:
        print("No valid transactions.")
        return



def get_last_block():
    best = None
    for fname in list_block_files():
        path = os.path.join(BLOCKS_DIR, fname)
        try:
            with open(path, "r") as f:
                blk = json.load(f)
        except Exception:
            # print(f"[skip] unreadable file: {fname}")
            continue

        header = blk.get("header")
        body   = blk.get("body")
        if not isinstance(header, dict) or not isinstance(body, list):
            # print(f"[skip] non-block JSON: {fname}")
            continue

        h = header.get("height")
        if not isinstance(h, int):
            # print(f"[skip] invalid height in: {fname}")
            continue

        if best is None or h > best[0]:
            best = (h, fname, blk)
    return best


def create_block():
    global valid_transactions, included_files
    if not valid_transactions:           
        return

    txids = [t["txid"] for t in valid_transactions]
    body_hash = hashlib.sha256(json.dumps(valid_transactions, separators=(',', ':')).encode()).hexdigest()

    last = get_last_block()
    if last:
        prev_height, prev_fname, _ = last
        height = prev_height + 1
        prev_hash = prev_fname.replace(".json", "")
    else:
        height = 0
        prev_hash = "NA"

    header = {
        "height": height,
        "timestamp": int(time.time()),
        "previousblock": prev_hash,
        "merkle_root": merkle_root(txids),
        "hash": body_hash
    }
    block_obj = {"header": header, "body": valid_transactions}

    fname = hashlib.sha256(canonical(header).encode()).hexdigest() + ".json"
    out_path = os.path.join(BLOCKS_DIR, fname)
    with open(out_path, "w") as f:
        json.dump(block_obj, f, indent=2)

    print(f"Block saved as {out_path}")

    # move only those we included
    for filename in included_files:
        shutil.move(os.path.join(PENDING_DIR, filename),
                    os.path.join(PROCESSED_DIR, filename))
    print("Transactions processed and moved.")

    # reset for next loop
    valid_transactions = []
    included_files = []


def validate_transaction(tx, utxos):
    # Structure
    if "txid" not in tx or "body" not in tx or "inputs" not in tx:
        return False
    body = tx["body"]
    if "inputs" not in body or "outputs" not in body:
        return False

    # txid integrity
    expected_txid = hashlib.sha256(canonical(body).encode()).hexdigest()
    if tx["txid"] != expected_txid:
        return False

    # outputs sane
    total_out = 0
    for o in body["outputs"]:
        if "value" not in o or "address" not in o:
            return False
        if not isinstance(o["value"], int) or o["value"] < 0:
            return False
        total_out += o["value"]

    # inputs: signatures + ownership + sum values from UTXO set
    body_bytes = canonical(body).encode()
    seen_inputs = set()
    total_in = 0
    for inp in tx["inputs"]:
        for k in ("prev_txid", "prev_index", "pubkey", "signature"):
            if k not in inp:
                return False

        key = f"{inp['prev_txid']}:{inp['prev_index']}"
        if key in seen_inputs:
            return False
        seen_inputs.add(key)

        utxo = utxos.get(key)
        if not utxo:
            return False  # double-spend or missing UTXO

        # verify signature over body
        if not verify_signature(inp["pubkey"], body_bytes, inp["signature"]):
            return False

        # enforce ownership: pubkey address must match the UTXO’s address
        if address_from_pub(inp["pubkey"]) != utxo["address"]:
            return False

        total_in += utxo["value"]

    if total_out > total_in:
        return False  # overspend

    return True






#process_pending_transactions()
#create_block()

#if we need to run in the background add:

while True:
    process_pending_transactions()
    if valid_transactions:   
        create_block()
    print("Waiting for new transactions...")
    time.sleep(5)












