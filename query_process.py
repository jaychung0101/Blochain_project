import json, socket, time, utils
from multiprocessing import Manager, Process

# receive processed transactions from execution_engine
def receive(processed_tx):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as querySocket:
        querySocket.bind(('', 13000))
        print("query_process ready!")

        while True:
            tx, _ = querySocket.recvfrom(2048)

            tx = tx.decode('utf-8')
            tx = json.loads(tx)
            
            processed_tx.append(tx)


if __name__ == "__main__":
    with Manager() as manager:
        processed_tx = manager.list()
        receive_process = Process(target=receive, args=(processed_tx,))
        receive_process.start()

        time.sleep(0.1)
        while True:
            query = input("% ")

            # show processed transactions
            if query=="snapshot transactions":
                for index, tx in enumerate(processed_tx):
                    utils.query_tx_print(index, tx)
            
            # show current UTXO set
            elif query=="snapshot utxoset":
                with open("json/UTXOes.json", "r") as UTXO_set:
                    utxoes = json.load(UTXO_set)

                for index, utxo in enumerate(utxoes):
                    utils.query_utxo_print(index, utxo)
                    print()
                    
            elif query=="exit":
                break
            else:
                print("Invalid query")
        
        receive_process.terminate()
        receive_process.join()
