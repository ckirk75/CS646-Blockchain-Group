import os 
import json
import time
import hashlib
import shutil
#  Initialize block height counter
blockheight = 0
# transaction array
transactions = []
# block array
blocks = []
#load in directories to read transactions
#replace with where your path for the transaction directories
'''
PENDING_DIR = r"E:\VSCode\Blockchain\PendingTransactions"
PROCESSED_DIR = r"E:\VSCode\Blockchain\ProcessedTransactions"
BLOCKS_DIR = r"E:\VSCode\Blockchain\Blocks"
'''
#create the path if dont exist
PENDING_DIR = "PendingTransactions" # holds new transactions waiting to be added to blocks
PROCESSED_DIR = "ProcessedTransactions" # stores transactions that have already been included in a block
BLOCKS_DIR = "Blocks" # this is the folder to store generated blocks 
os.makedirs(PENDING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(BLOCKS_DIR, exist_ok=True)
def process_pending_transactions():
    pending_files = os.listdir(PENDING_DIR)
    transactions = []
    if not pending_files:
        print("No pending transactions to include in block.")
        return [], []
    for filename in pending_files:
        with open(os.path.join(PENDING_DIR, filename), 'r') as f:
            content = json.load(f)
        transactions.append({
            "hash": filename.replace(".json", ""),
            "content": content
        })

    return transactions, pending_files
def get_last_block():
    for fname in os.listdir(BLOCKS_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(BLOCKS_DIR, fname), 'r') as f:
                block = json.load(f)
                height = block['header']['height']
                blocks.append((height, fname, block))
    if blocks:
        return max(blocks, key=lambda x: x[0])  # Return block with highest height
    return None  # No previous block
def create_block():
    transactions, pending_files = process_pending_transactions()
    if not transactions:
        return
    for tx in transactions:
        print("Including transaction:", tx["hash"])
    # Create block body and hash it
    block_body = transactions
    body_hash = hashlib.sha256(json.dumps(block_body, separators=(',', ':')).encode()).hexdigest()
    # Determine block height and previous hash
    last_block = get_last_block()
    if last_block:
        prev_height, prev_filename, prev_block = last_block
        blockheight = prev_height + 1
        prev_hash = prev_filename.replace(".json", "")
    else:
        blockheight = 0
        prev_hash = "NA"
    # Header
    timestamp = time.time()
    header = {
        "height": blockheight,
        "timestamp": timestamp,
        "previousblock": prev_hash,
        "hash": body_hash
    }
    header_string = json.dumps(header)
    # Create block
    data = {
        "header": header,
        "body": block_body
    }
    data_string = json.dumps(data)
    # Hash filename
    hash_filename = hashlib.sha256(json.dumps(header, separators=(',', ':')).encode()).hexdigest()
    block_filepath = os.path.join(BLOCKS_DIR, f"{hash_filename}.json")
    with open(block_filepath, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Block saved as {block_filepath}")
    # Move transactions to processed
    for filename in pending_files:
        shutil.move(
            os.path.join(PENDING_DIR, filename),
            os.path.join(PROCESSED_DIR, filename)
        )
    print("Transactions processed and moved.")
    print(header_string)
    print(data_string)
#process_pending_transactions()
#create_block()
#if we need to run in the background add:
while True:
    # call the same block creation logic
    process_pending_transactions()
    create_block()
    print("Waiting for new transactions...")
    time.sleep(30)