import json
import hashlib
import time
import uuid
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


'''
first draft of the transaction will come back and refine later working on  the block file now
'''
# Ensure the pending transactions folder exists
# have a transaction folder to hold transactions and pending transactions
PENDING_DIR = "PendingTransactions"
os.makedirs(PENDING_DIR, exist_ok=True)
TX_REQUESTS_DIR = "tx_requests"
os.makedirs(TX_REQUESTS_DIR, exist_ok=True)

timestamp = time.time()
from_ = input("enter the account to transfer from: ")
sender = input("Sender wallet (A/B/C): ").strip().upper()
to = input("enter the account to transfer to: ")
receiver = input("Receiver wallet (A/B/C or paste address): ").strip()
amount = input("enter the amount to transfer:")
data = {
    "type": "draft",
    "timestamp": timestamp,
    "from": from_,
    "sender_wallet": sender,
    "to": to,
    "receiver": receiver,
    "amount": amount
}

# Serialize the JSON without whitespace
transaction_json = json.dumps(data, separators=(',', ':'))

#hash string ie file name
hash = hashlib.sha256(transaction_json.encode()).hexdigest()


filename = os.path.join(TX_REQUESTS_DIR, f"{hash}.json")
with open(filename, "w") as file:
    file.write(transaction_json)

print(f"Data successfully saved to {filename}")






