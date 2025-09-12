import json # working with JSON objects especially to store transactions
import time # current unix timestamp
import hashlib # creating SHA-256 hash of the transaction
import os # creating folders and working with files 
def create_transaction():
    # collecting transaction information from the user
    from_user = input("From: ")      # The person who is sending money
    to_user = input("To: ")          # The person who is receiving money
    amount = float(input("Amount: "))  # amount of money
    # Build transaction object
    transaction = {
        "timestamp": int(time.time()),  # current time (in Unix format)
        "from": from_user,
        "to": to_user,
        "amount": amount
    }
    # Converting to JSON string (no spaces or line breaks)
    transaction_str = json.dumps(transaction, separators=(",", ":"))
    # Creating SHA-256 hash of the transaction
    tx_hash = hashlib.sha256(transaction_str.encode()).hexdigest()
    # Make sure pending folder exists, if not we need to create it
    os.makedirs("pending", exist_ok=True)
    # Save file inside "pending" folder, with hash as the filename
    filename = f"pending/{tx_hash}.json"
    with open(filename, "w") as f:
        f.write(transaction_str)
    print(f"✅Transaction saved as {filename}")
if __name__ == "__main__":
    create_transaction()