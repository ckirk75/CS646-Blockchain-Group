import time
import hashlib
import json
import os

# Create the folder where transactions will be saved
# This avoids errors if the folder doesn't already exist
os.makedirs("pending_transaction_folder", exist_ok=True)

# Represents a single transaction from one user to another
class Transaction:
    """Stores basic details for a user transaction,including sender, receiver, amount,remarks ,and timestamp."""
    def __init__(self, from_user, to_user, amount, remarks):
        self.from_user= from_user
        self.to_user = to_user
        self.amount = amount
        self.remarks = remarks
        self.timestamp = int(time.time()) # Record current time in seconds

    def to_dict(self):
        # Convert the transaction into a dictionary format
        # Makes it easier to convert to JSON and save to a file
        return {
            "timestamp": self.timestamp,
            "from": self.from_user,
            "to": self.to_user,
            "amount": self.amount ,
            "remarks": self.remarks ,
        }

# Ask the user to enter details for a transaction
def collect_transaction_info():
    while True:
        sender = input("Name of the sender : ").strip()
        if sender:
            break
        print("Sender's name cannot be empty.")

    while True:
        receiver = input("Name of the receiver : ").strip()
        if receiver:
            break
        print("Receiver's name cannot be empty.")

    while True:
        try:
            amount = float(input("Amount to send: "))
            if amount > 0:
                break
            else:
                print("Amount must be greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a number (e.g. 3.78 or 400).")

    # Return a Transaction object containing all collected data
    remarks =input("Enter any remarks or messages(optional):").strip()
    return Transaction(sender, receiver, amount, remarks)

if __name__ == "__main__":
    # Collect transaction data from the user
    new_transaction = collect_transaction_info()

    # Convert the transaction to JSON string format
    json_string = json.dumps(new_transaction.to_dict(), separators=(",", ":"))

    # Generate a unique hash for the transaction (used as the filename)
    transaction_hash= hashlib.sha256(json_string.encode()).hexdigest()


    # Define the output path using the unique hash
    filename = f"pending_transaction_folder/{transaction_hash}.json"

    # Write the transaction JSON to a file for later processing or review
    with open(filename, "w") as file:
        file.write(json_string)

    # Confirm that the transaction was successfully saved
    # Confirm that the transaction was successfully saved
    print(f"✅ Your transaction was saved successfully to pending_transaction_folder/{transaction_hash[:8]}...")
    print("Waiting to be added to a block...")

