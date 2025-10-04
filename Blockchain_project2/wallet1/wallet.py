import os
import json
import hashlib
import time
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# -------------------- Files & Directories --------------------
WALLET_KEY_FILE = "wallet_private.pem"
WALLET_ADDRESS_FILE = "wallet_address.txt"
PENDING_DIR = r"C:\Users\pooja\OneDrive\Desktop\Blockchain_project2\PendingTransactions"
BLOCKS_DIR = r"C:\Users\pooja\OneDrive\Desktop\Blockchain_project2\Blocks"

os.makedirs(PENDING_DIR, exist_ok=True)
os.makedirs(BLOCKS_DIR, exist_ok=True)

# -------------------- Wallet --------------------
def create_or_load_wallet():
    if os.path.exists(WALLET_KEY_FILE):
        with open(WALLET_KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        print("Loaded existing wallet.")
    else:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(WALLET_KEY_FILE, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                )
            )
        print("New wallet created and saved.")

    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    address = hashlib.sha256(pub_bytes).hexdigest()
    with open(WALLET_ADDRESS_FILE, "w") as f:
        f.write(address)
    return private_key, address

# -------------------- Create Signed Transaction --------------------
def create_transaction(private_key, sender, receiver, amount):
    tx = {
        "timestamp": time.time(),
        "from": sender,
        "to": receiver,
        "amount": amount
    }
    tx_data = json.dumps(tx, separators=(',', ':')).encode()

    # Sign the transaction
    signature = private_key.sign(
        tx_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    tx["signature"] = signature.hex()

    # Save to PendingTransactions folder
    filename = os.path.join(PENDING_DIR, f"{hashlib.sha256(tx_data).hexdigest()}.json")
    with open(filename, "w") as f:
        json.dump(tx, f, indent=4)

    print(f"Transaction saved → {filename}")

# -------------------- Check Balance --------------------
def check_balance(address):
    balance = 0
    if not os.path.exists(BLOCKS_DIR):
        print("No blocks found yet.")
        return balance

    for fname in os.listdir(BLOCKS_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(BLOCKS_DIR, fname), "r") as f:
                block = json.load(f)
                for tx in block.get("body", []):
                    tx_data = tx.get("content", tx)
                    # Sent currency
                    if tx_data.get("from") == address:
                        balance -= tx_data.get("amount", 0)
                    # Received currency
                    if tx_data.get("to") == address:
                        balance += tx_data.get("amount", 0)
    return balance

# -------------------- Main --------------------
if __name__ == "__main__":
    private_key, my_address = create_or_load_wallet()
    print("Your Wallet Address:", my_address)

    while True:
        choice = input("\nOptions:\n"
                       "1. Show My Address\n"
                       "2. Create Transaction\n"
                       "3. Check My Balance\n"
                       "4. Check Another Wallet Balance\n"
                       "5. Exit\nEnter: ")

        if choice == "1":
            print("Your Address:", my_address)
        elif choice == "2":
            receiver = input("Enter recipient wallet address: ")
            amount = float(input("Enter amount: "))
            create_transaction(private_key, my_address, receiver, amount)
        elif choice == "3":
            print("Your Balance:", check_balance(my_address))
        elif choice == "4":
            other = input("Enter the wallet address to check: ")
            print(f"Balance of {other}:", check_balance(other))
        elif choice == "5":
            break
        else:
            print("Invalid option, try again.")
