import json

# Return json folder contents to initial state
def main():
    try:
        with open("backup/transaction_backup.json", "r") as file:
            transactions = json.load(file)
    except FileNotFoundError:
        transactions = []

    try:
        with open("backup/utxo_backup.json", "r") as file:
            utxoes = json.load(file)
    except FileNotFoundError:
        utxoes = []
        
    with open("json/transactions.json", "w") as file:
        json.dump(transactions, file, indent=4)
    with open("json/UTXOes.json", "w") as file:
        json.dump(utxoes, file, indent=4)

if __name__ == "__main__":
    main()