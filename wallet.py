import os
import json
import time
import hashlib

# files to store wallet and transactions
wallet_dir = "Wallets"
pending_dir = "Pending_Transactions"

# Create path files  if they don't exist
os.makedirs(wallet_dir, exist_ok=True)
os.makedirs(pending_dir, exist_ok=True)

# File paths for private and public keys
private_key_file = os.path.join(wallet_dir, "wallet_private.pem")
public_key_file = os.path.join(wallet_dir, "wallet_public.pem")

# Initialize wallet i.e. create private/public key pair if it doesn't exist
if not os.path.exists(private_key_file):
    # Generating private/public keys (placeholder)
    private_key = "private_key_placeholder"
    public_key = "public_key_placeholder"
    
    with open(private_key_file, "w") as f:
        f.write(private_key)
    
    with open(public_key_file, "w") as f:
        f.write(public_key)

    print("Wallet initialized successfully!")
else:
    print("Wallet already exists. Loading wallet...")

# Load the public key and generate the wallet address
def get_wallet_address():
    with open(public_key_file, "r") as f:
        public_key = f.read()
    
    address = hashlib.sha256(public_key.encode()).hexdigest()[:40]  # Use first 40 characters as the address
    return address

# function to create a transaction and save it to a file
def create_transaction(to, amount):
    timestamp = time.time() 
  # Get wallet address
    from_address = get_wallet_address()  
    
    #  transaction data
    transaction = {
        "timestamp": timestamp,
        "from": from_address,
        "to": to,
        "amount": amount,
        "signature": ""  # Placeholder for signature
    }

    # like mock signature
    transaction_json = json.dumps(transaction, separators=(',', ':'))
    signature = hashlib.sha256(transaction_json.encode()).hexdigest()  # Simple hashing as signature
    transaction["signature"] = signature

    # saving transaction to the pending transactions directory
    transaction_hash = hashlib.sha256(transaction_json.encode()).hexdigest()
    filename = os.path.join(pending_dir, f"{transaction_hash}.json")
    
    with open(filename, "w") as f:
        f.write(transaction_json)
    
    print(f"Transaction saved as {filename}")
    return filename

# function to check balance (just like a simple placeholder for now)
def check_balance(address):
    print(f"Checking balance for wallet address: {address}")
    balance = 100  # Placeholder balance (in a real system, you'd check the blockchain)
    print(f"Balance of {address}: {balance} units")
    return balance

# real program
# trial of  a wallet and transaction interaction
print("Wallet Address:", get_wallet_address())

# user creates a transaction
to_address = input("Enter recipient wallet address: ")
amount = float(input("Enter amount to send: "))
create_transaction(to_address, amount)

# checking balance of the current wallet
address = get_wallet_address()
check_balance(address)

# check balance for another address
check_other = input("check balance for another wallet (yes/no): ").strip().lower()