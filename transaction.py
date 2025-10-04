import json
import hashlib
import time
import os

'''
first draft of the transaction will come back and refine later working on  the block file now
'''
# Ensure the pending transactions folder exists
# have a transaction folder to hold transactions and pending transactions
#PENDING_DIR = r"E:\VSCode\Blockchain\PendingTransactions"
PENDING_DIR = "PendingTransactions"


os.makedirs(PENDING_DIR, exist_ok=True)

timestamp = time.time()
from_ = input("enter the account to transfer from: ")
to = input("enter the account to transfer to: ")
amount = input("enter the amount to transfer:")
data = {
    "timestamp": timestamp,
    "from": from_,
    "to": to,
    "amount": amount
}


# Serialize the JSON without whitespace
transaction_json = json.dumps(data, separators=(',', ':'))

#hash string ie file name
hash = hashlib.sha256(transaction_json.encode()).hexdigest()

filename = os.path.join(PENDING_DIR, f"{hash}.json")
with open(filename, "w") as file:
    file.write(transaction_json)

print(f"Data successfully saved to {filename}")
