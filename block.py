#Proof of work? You're looking at it . - A_K

#Import these libraries to handle json
# work with files(os,shutil)
# do cryptographic hashing(hashlib) and
# record time
import os
import json
import hashlib
import time
import shutil

# Create required folders if they don't exist
os.makedirs("pending_transaction_folder", exist_ok=True)
os.makedirs("processed_transaction_folder", exist_ok=True)
os.makedirs("blocks", exist_ok=True)

class Block:
    """A block containing a list of transactions and a header."""

    def __init__(self, transactions, height, previous_block_hash):
        self.transactions = transactions
        self.height = height
        self.previous_block_hash = previous_block_hash
        self.timestamp = int(time.time())
        self.body = self.create_body()
        self.body_hash = self.hash_data(self.body)

        self.header = {
            "height": self.height,
            "timestamp": self.timestamp,
            "previousblock": self.previous_block_hash,
            "hash": self.body_hash
        }

        # This hash will be used as filename
        self.header_hash = self.hash_data(self.header)


    def __repr__(self):
        return f"<Block height={self.height}, hash={self.header_hash[:8]}...>"
    def create_body(self):
        """Create the body list containing hash + content of each transaction."""
        return [{"hash": tx["hash"], "content": tx["content"]} for tx in self.transactions]

    @staticmethod
    def hash_data(data):
        """Generate SHA-256 hash of a dictionary (sorted JSON string)."""
        json_string = json.dumps(data, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(json_string.encode()).hexdigest()

    def to_dict(self):
        return {"header": self.header, "body": self.body}

    def save_to_file(self):
        filename = f"blocks/{self.header_hash}.json"
        with open(filename, "w") as file:
            json.dump(self.to_dict(), file, indent=4)
        print(f" Block saved as '{self.header_hash}.json' in 'blocks/' folder.")


def read_pending_transactions():
    """Read and return all pending transactions from the folder."""
    tx_list = []
    for file in os.listdir("pending_transaction_folder"):
        if file.endswith(".json"):
            path = os.path.join("pending_transaction_folder", file)
            with open(path, "r") as f:
                try:
                    content = json.load(f)
                    tx_list.append({
                        "hash": file.split(".")[0],
                        "content": content,
                        "_filename": file
                    })
                except json.JSONDecodeError:
                    print(f" Skipped invalid JSON: {file}")
    return tx_list


def get_latest_block_info():
    """Return (latest block hash, next height) by scanning 'blocks/'."""
    block_files = [f for f in os.listdir("blocks") if f.endswith(".json")]
    latest_height = -1
    latest_hash = "NA"

    for file in block_files:
        path = os.path.join("blocks", file)
        try:
            with open(path, "r") as f:
                block_data = json.load(f)
                height = block_data["header"].get("height", -1)
                if height > latest_height:
                    latest_height = height
                    latest_hash = file.split(".")[0]
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f" Failed to process block file '{file}': {e}")
            continue

    return latest_hash, latest_height + 1


def move_transactions(tx_list):
    """Move processed transactions to the 'processed_transaction_folder'."""
    for tx in tx_list:
        src = os.path.join("pending_transaction_folder", tx["_filename"])
        dst = os.path.join("processed_transaction_folder", tx["_filename"])
        shutil.move(src, dst)

def main():
        print("\n Checking for pending transactions...")
        pending_txns = read_pending_transactions()

        if not pending_txns:
            print("No pending transactions to include in a block.")
            return

        #  1. Show number of transactions
        print(f" Included {len(pending_txns)} transaction(s) in the block.")

        prev_hash, next_height = get_latest_block_info()

        #  2. Print previous block hash
        print(f"Linked to previous block: {prev_hash}")

        #  3. Custom block creation message
        block = Block(pending_txns, next_height, prev_hash)
        print(f"\n Creating new block at height {block.height} with hash preview: {block.header_hash[:8]}...")

        block.save_to_file()
        move_transactions(pending_txns)

        print(" Transactions moved to processed folder.")
        print(" Hope this block doesn't get blocked!")

if __name__ == "__main__":
    main()