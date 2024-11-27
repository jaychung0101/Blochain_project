import hashlib
import utils
from ecdsa import VerifyingKey, SECP256k1

# return result applying sha256 hash twice
def sha256_twice(tx_input, tx_output, i_scriptPubKey=None):
    sha256_hash = hashlib.sha256()

    i_ptxid, i_vout, i_scriptSig = utils.vin_load(tx_input)
    sha256_hash.update(i_ptxid.encode())
    sha256_hash.update(str(i_vout).encode())
    if i_scriptPubKey:
        sha256_hash.update(i_scriptPubKey.encode())
    else:
        sha256_hash.update(i_scriptSig.encode())

    for vout in tx_output:
        amount, o_scriptPubKey = utils.vout_load(vout)
        sha256_hash.update(str(amount).encode())
        sha256_hash.update(o_scriptPubKey.encode())

    result = hashlib.sha256(sha256_hash.digest()).digest()
    return result


# return result applying sha256->ripemd160
def sha256_ripemd160(input_string):
    sha256_hash = hashlib.sha256(input_string.encode()).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    return ripemd160_hash.hex()


# verifying signature
def sig_validation_check(pubKey, signature, verifying_tx):
    public_key = VerifyingKey.from_string(bytes.fromhex(pubKey), curve=SECP256k1)
    signature = bytes.fromhex(signature)

    try:
        return public_key.verify(signature, verifying_tx)
    except Exception as e:
        return False