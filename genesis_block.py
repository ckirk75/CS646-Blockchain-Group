
import os, json, time, hashlib

BLOCKS_DIR = "Blocks"  
ADDRS_FILE = "addresses.json"

os.makedirs(BLOCKS_DIR, exist_ok=True)

def canonical(obj):
    return json.dumps(obj, separators=(',', ':'), sort_keys=True)

def merkle_root(txids):
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

# 1) Load addresses.json — you must have run wallet_A and wallet_B (and C) once
if not os.path.exists(ADDRS_FILE):
    raise SystemExit("addresses.json not found. Run each wallet once to register addresses, then re-run genesis.")

with open(ADDRS_FILE, "r") as f:
    book = json.load(f)

# Fund all labels present (A/B/C...) with same start balance
START_BAL = 1_000_000
recipients = []
for label, info in book.items():
    addr = info.get("address")
    if isinstance(addr, str) and len(addr) >= 40:  # naive sanity check
        recipients.append({"address": addr, "value": START_BAL})

if not recipients:
    raise SystemExit("No valid addresses found in addresses.json. Run wallets first.")

# 2) Build a coinbase-style tx (no inputs)
coinbase_body = {
    "timestamp": int(time.time()),
    "inputs": [],                   # coinbase has no inputs
    "outputs": recipients           # fund each wallet
}
coinbase_tx = {
    "txid": hashlib.sha256(canonical(coinbase_body).encode()).hexdigest(),
    "body": coinbase_body,
    "inputs": []                    # keep field present to match your tx schema
}

# 3) Assemble the genesis block (height 0)
txids = [coinbase_tx["txid"]]
header = {
    "height": 0,
    "timestamp": int(time.time()),
    "previousblock": "NA",          # matches your block.py field name
    "merkle_root": merkle_root(txids),
    # optional body hash (your block.py writes one when creating blocks; harmless to include here)
    "hash": hashlib.sha256(json.dumps([coinbase_tx], separators=(',', ':')).encode()).hexdigest()
}
block = {"header": header, "body": [coinbase_tx]}

# 4) File name = sha256(canonical(header))
fname = hashlib.sha256(canonical(header).encode()).hexdigest() + ".json"
out_path = os.path.join(BLOCKS_DIR, fname)


# Safety: allow writing genesis if only legacy blocks exist (no new-format blocks found)
def _is_new_format_block(obj):
    if not isinstance(obj, dict):
        return False
    if "header" not in obj or "body" not in obj or not isinstance(obj["body"], list):
        return False
    # new format has tx objects with 'txid' and nested 'body'
    return any(isinstance(tx, dict) and "txid" in tx and "body" in tx for tx in obj["body"])

existing_files = [n for n in os.listdir(BLOCKS_DIR) if n.endswith(".json")]
new_format_found = False
legacy_count = 0

for name in existing_files:
    path = os.path.join(BLOCKS_DIR, name)
    try:
        with open(path, "r") as f:
            obj = json.load(f)
        if _is_new_format_block(obj):
            new_format_found = True
            break
        else:
            legacy_count += 1
    except Exception:
        # unreadable counts as legacy/ignored
        legacy_count += 1

if new_format_found:
    print(f"[genesis] Found existing new-format block(s) in {BLOCKS_DIR}/. Skipping genesis to avoid conflicts.")
else:
    if legacy_count:
        print(f"[genesis] Detected {legacy_count} legacy block file(s) — ignoring them.")
    with open(out_path, "w") as f:
        json.dump(block, f, indent=2)
    print(f"[genesis] Wrote {out_path}")
    print("[genesis] Funded recipients:")
    for r in recipients:
        print(" -", r["address"][:16], "...", r["value"])
