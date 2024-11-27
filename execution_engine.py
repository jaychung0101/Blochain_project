# Execution Engine
import json, utils, socket

class ScriptExecutor:
    def __init__(self, pay_type, scriptSig, scriptPubKey, verifying_tx):
        self.script_queue = [] # remaining script
        self.stack = [] # data(sig, pubKey, TRUE, ...)
        self.condition_stack = [] # manage nested conndition clauses
        self.pay_type = pay_type
        self.verifying_tx = verifying_tx # signature verification target
        self.fail = None # save fail location
        self.OP_CODES = {
            "DUP": self.op_dup, 
            "HASH": self.op_hash, 
            "EQUAL": self.op_equal, 
            "EQUALVERIFY": self.op_equalverify, 
            "CHECKSIG": self.op_checksig, 
            "CHECKSIGVERIFY": self.op_checksigverify, 
            "CHECKMULTISIG": self.op_checkmultisig, 
            "CHECKMULTISIGVERIFY": self.op_checkmultisigverify,     
            "IF": self.op_if, 
            "ELSE": self.op_else, 
            "ENDIF": self.op_endif, 
            "CHECKFINALRESULT": self.op_checkfinalresult
        }

        # P2SH
        if pay_type == 1:
            scriptSig = scriptSig.split()

            # extract redeem script
            str_id = 0
            for index, token in enumerate(scriptSig):
                if token=="<":
                    self.script_queue = scriptSig[:index]
                    str_id = index+1
                elif token==">":
                    self.script_queue.append(" ".join(scriptSig[str_id:index]))

            scriptPubKey = scriptPubKey.split()
            for token in scriptPubKey:
                self.script_queue.append(token)

        # Pay without P2SH
        else:
            script = " ".join([scriptSig, scriptPubKey])
            self.script_queue = script.split()


    # execute remaining script
    def execution(self):
        while self.script_queue:
            token = self.script_queue.pop(0)
            if token in self.OP_CODES:
                self.OP_CODES[token]()
            else:
                self.stack.append(token)

            if self.fail:
                return False, self.fail
        
        self.op_checkfinalresult()
        if self.fail:
                return False, self.fail

        return True, self.fail
    

    def op_dup(self):
        top = self.stack.pop()
        self.stack.append(top)
        self.stack.append(top)


    def op_hash(self):
        input_string = self.stack.pop()
        result = utils.sha256_ripemd160(input_string)
        self.stack.append(result)


    def op_equal(self, verify=False):
        top1=self.stack.pop()
        top2=self.stack.pop()

        if(top1==top2):
            if verify:
                return True
            self.stack.append("TRUE")
        else: 
            if verify:
                return False
            self.stack.append("FALSE")


    def op_equalverify(self):
        val = self.op_equal(True)
        if not val: 
            self.fail = "EQUALVERIFY"

        # if P2SH, execute redeem script
        if self.pay_type == 1 and len(self.script_queue) == 0:
            scriptX = self.stack.pop()
            self.script_queue = scriptX.split()
            self.pay_type = 0
            self.execution()


    def op_checksig(self, verify=False):
        pubKey = self.stack.pop()
        signature = self.stack.pop()
        
        val = utils.sig_validation_check(pubKey, signature, self.verifying_tx)
        if val:
            if verify:
                return True
            self.stack.append("TRUE")
        else:
            if verify:
                return False
            self.stack.append("FALSE")


    def op_checksigverify(self):
        val = self.op_checksig(True)
        if not val:
            self.fail = "CHECKSIGVERIFY"


    def op_checkmultisig(self, verify=False):
        pubKeys = []
        sigs = []

        N = int(self.stack.pop())
        for _ in range(N):
            pubKey = self.stack.pop()
            pubKeys.append(pubKey)
        
        M = int(self.stack.pop())
        for _ in range(M):
            sig = self.stack.pop()
            sigs.append(sig)

        val = 0
        for sig in sigs:
            for pubkey in pubKeys:
                if utils.sig_validation_check(pubkey, sig, self.verifying_tx):
                    val += 1
                    break

        if val==M:
            if verify:
                return True
            self.stack.append("TRUE")
        else:
            if verify:
                return False
            self.stack.append("FALSE")


    def op_checkmultisigverify(self):
        val = self.op_checkmultisig(True)
        if not val:
            self.fail = "CHECKMULTISIGVERIFY"


    def op_if(self):
        condition = self.stack.pop()

        if condition == "TRUE":
            self.condition_stack.append((1, True))
        else:
            self.condition_stack.append((1, False))
            condition_cnt = len(self.condition_stack)
            while True:
                token = self.script_queue[0]
                if token == "IF": 
                    self.condition_stack.append((1, None)) # For counting ELSE
                elif token == "ELSE": 
                    if len(self.condition_stack)==condition_cnt:
                        break
                    else:
                        self.condition_stack.append((-1, None))
                elif token == "ENDIF": self.op_endif()
                self.script_queue.pop(0)


    def op_else(self):
        top = self.condition_stack[-1][1]
        if top == False:
            self.condition_stack.append((-1, False))
        elif top == True:
            self.condition_stack.append((-1, True))
            condition_cnt = len(self.condition_stack)
            while True:
                token = self.script_queue[0]
                if token == "IF": 
                    self.condition_stack.append((1, None)) # For counting ELSE
                elif token == "ELSE": 
                    self.condition_stack.append((-1, None))
                elif token == "ENDIF": 
                    if len(self.condition_stack) == condition_cnt:
                        break
                    self.op_endif()
                self.script_queue.pop(0)


    def op_endif(self):
        # IF - ENDIF
        if self.condition_stack[-1][0] == 1:
            self.condition_stack.pop()
        
        # IF - ELSE - ENDIF
        else:
            self.condition_stack.pop()
            self.condition_stack.pop()


    def op_checkfinalresult(self): # check stack that remaining element is only "TRUE"
        if len(self.stack) > 1 or len(self.stack) < 1:
            self.fail = "CHECKFINALRESULT"
        elif self.stack[0] != "TRUE":
            self.fail = "CHECKFINALRESULT"
        else:
            return


def tx_processor():
    transaction_path = "json/transactions.json"
    UTXO_path = "json/UTXOes.json"

    # load transaction_set
    with open(transaction_path, "r") as transaction_set:
        transactions = json.load(transaction_set)
    
    # processing per transaction
    for tx in transactions:

        # time(sec) per processing transaction
        utils.loading_print(5)
        
        tx_input = tx["vin"]
        tx_output = tx["vout"]
        i_ptxid, i_vout, i_scriptSig = utils.vin_load(tx_input)

        # transaction validation check
        val = True
        
        # load UTXO_set
        with open(UTXO_path, "r") as UTXO_set:
            UTXOes = json.load(UTXO_set)
        UTXO = utils.utxo_find(UTXOes, i_ptxid, i_vout)

        if UTXO:
            input_amount, scriptPubKey = utils.utxo_load(UTXO)
            output_amount = utils.vout_amount_sum(tx_output)
            
            # amount validation check
            if input_amount >= output_amount:
                # for signature verification
                verifying_tx = utils.sha256_twice(tx_input, tx_output, scriptPubKey)

                # check pay type whether P2SH or not
                pay_type = utils.pay_typecheck(scriptPubKey)
                
                executor = ScriptExecutor(pay_type, i_scriptSig, scriptPubKey, verifying_tx)
                validator, fail_location = executor.execution()
                
                # Transaction is valid
                if validator:
                    utils.tx_print(tx)
                    print("\nremove UTXO: ")
                    utils.utxo_print(json.dumps(UTXO, indent=4), "red")
                    UTXOes.remove(UTXO)

                    print("\nnew UTXO: ")
                    for index, vout in enumerate(tx_output):
                        new_UTXO={
                            "ptxid":tx["txid"],
                            "vout": index,
                            "amount": vout["amount"],
                            "scriptPubKey": vout["scriptPubKey"]
                        }
                        UTXOes.append(new_UTXO)
                        utils.utxo_print(json.dumps(new_UTXO, indent=4), "cyan")
                        print()

                    # Edit UTXO set
                    with open(UTXO_path, "w") as file:
                        json.dump(UTXOes, file, indent=4)
                else: # script execution error
                    utils.tx_print(tx, error=fail_location)
                    val = False

            else: # Input amount error
                utils.tx_print(tx, error="Invalid input amount")
                val = False

        else: # Trasaction reference invalid UTXO
            utils.tx_print(tx, error="Transaction reference invalid UTXO")
            val = False

        # send processed transaction to query process
        message = {
            "txid": tx["txid"],
            "validity check": val
            }
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as executionSocket:    
            executionSocket.bind(('localhost', 12345))
            executionSocket.sendto(json.dumps(message).encode(), ("127.0.0.1", 13000))
    
    print("all transactions processed")

if __name__ == "__main__":
    tx_processor()