# 프로젝트 개요
***비트코인 Full nodes에서 진행되는 트랜잭션 검증을 흉내 내는 가상의 스택 기반
실행 엔진을 설계하고 구현한다***

1. `json/transactions.json`에 들어있는 트랜잭션을 하나씩 가져와 해당 트랜잭션이 참조하는 UTXO의 스크립트를 연계하여 실행한다.
2. 스택 기반의 실행 엔진은 트랜잭션의 유효성을 검증한다.
    - 참조되는 UTXO의 amount가 output들의 amount의 합보다 큰지 검사
    - 연계 실행된 unlockingScript + lockingScript의 결과가 유효한지 검사
3. 유효성 검사를 통과한 경우, 참조된 UTXO를 UTXO 집합에서 지우고 새로운 UTXO들을 저장한다.
4. 스택에서 처리한 트랜잭션 목록과 현재 UTXO 집합을 쿼리 프로세스에서 질의해 확인 할 수 있다.

### 조건
1. script의 문법적 오류(syntax error)는 없다고 가정한다.
2. 트랜잭션의 실행 결과 생기는 UTXO들의 lockingScript는 편의상 모두 P2PKH 형식으로 설정한다.
3. 초기 트랜잭션의 실행 결과 생기는 UTXO들을 참조하는 트랜잭션은 없다.(키 관리의 번거로움)

### 프로젝트 실행
> ***Ubuntu 18.04.6 LTS 를 사용***
```shell
# pip install list
pip install ecdsa
pip install rich # 터미널 출력 개선
pip install ipykernel # transaction_generator.py 사용 시 설치
```
#### 1. `init.py`로 json 디렉토리 내 파일 초기화
`execution_engine.py`를 실행했을 경우 UTXO 집합이 업데이트 되므로 초기화 시켜준다.
```shell
python init.py
```

#### 2. `query_process.py`실행
`query_process.py`를 실행시켜 실행 엔진에서 처리한 트랜잭션을 수신할 수 있도록 한다.
```shell
python query_process.py
```

#### 3. `execution_engine.py`실행
트랜잭션 집합에서 트랜잭션을 하나씩 가져와 검증한다.
```shell
python execution_engine.py
```

#### 4. 쿼리 프로세스에서 정보 확인
쿼리 프로세스에서 아래 명령어를 통해 처리된 트랜잭션 목록과 현재 UTXO 집합을 가져온다.
```shell
# query_process.py
% snapshot transactions # 처리된 트랜잭션 목록 로드
% snapshot utxoset # 현재 UTXO 집합 로드
```

#### *초기 트랜잭션 집합*
|index|type|validity|note|path|scriptX|
|:-----:|:----:|:---:|:----:|----|-------|
|0|P2PKH|P|
|1|P2PKH|F|input amount < output amount|
|2|P2PKH|F|invalid signature|
|3|MULTISIGNATURE|P|2 of 3 MULTISIGNATURE|
|4|MULTISIGNATURE|F|invalid signature|
|5|P2SH|P||TRUE|IF 2 pubKey pubKey pubKey 3 CHECKMULTISIG ELSE DUP HASH pubKeyHash EQUALVERIFY CHECKSIG ENDIF|
|6|P2SH|P||FALSE|same as 5|
|7|P2SH|F|invalid signature||pubKey CHECKSIGVERIFY pubKey CHECKSIGVERIFY pubKey CHECKSIG|
|8|P2SH|P||TRUE|IF 2 pubKey pubKey pubKey 3 CHECKMULTISIG ELSE DUP HASH pubKeyHash EQUALVERIFY CHECKSIG ENDIF|
|9|P2SH|P|||pubKey CHECKSIG IF pubKey CHECKSIG IF pubKey CHECKSIG ENDIF ENDIF|
|10|P2PKH|F|invalid UTXO reference||||
|11|P2SH|P|condition clause with guard clause||HASH pubKeyHash EQUAL IF pubKey CHECKSIG ENDIF|
|12|P2SH|P|1 of 2 multisig with condition clause|FALSE|IF pubKey CHECKSIG ELSE pubKey CHECKSIG ENDIF|

***새로운 트랜잭션 및 UTXO 추가***
`transaction_generator.py` 
#### Essential Part 작성(공통)
|변수 이름|입력값|
|:---------:|------|
|vout_amount|트랜잭션 output에 들어갈 utxo 개수만큼 amount를 작성|
|vout_idx|input UTXO의 인덱스|
|utxo_amount|input UTXO의 amount|

&rightarrow; 트랜잭션 종류에 따라 아래 중 하나
#### 1. P2PKH 트랜잭션 생성
`#1` &rightarrow; `#2-1` &rightarrow; `#3` &rightarrow; `#4` 순으로 실행

#### 2. MULTISIGNATURE 트랜잭션 생성
|변수 이름|입력값|
|:---------:|------|
|m|m of n MULTISIGNATURE의 m(서명개수)|
|n|m of n MULTISIGNATURE의 m(pubKey 개수)|

`#1` &rightarrow; `#2-2` &rightarrow; `#3` &rightarrow; `#4` 순으로 실행

#### 3. P2SH 트랜잭션 생성
|변수 이름|입력값|
|:---------:|------|
|redeem_script|P2SH에서 사용될 scriptX|

> `#2-3-2`는 script종류에 따라 scriptSig와 path를 알맞게 설정할 것.

`#1` &rightarrow; `#2-3-1` &rightarrow; `#2-3-2` &rightarrow; `#3` &rightarrow; `#4` 순으로 실행

---
#### UTXO구조
```python
# UTXO구조
    {
        "ptxid": "<ptxid>",
        "vout": <index>,
        "amount": <amount>,
        "scriptPubKey": "<scriptPubKey>"
    }
```

#### 스택기반 실행엔진
```python
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


    def execution(self): # execute remaining script
    def op_dup(self):
    def op_hash(self):
    def op_equal(self, verify=False):
    def op_equalverify(self):
    def op_checksig(self, verify=False):
    def op_checksigverify(self):
    def op_checkmultisig(self, verify=False):
    def op_checkmultisigverify(self):
    def op_if(self):
    def op_else(self):
    def op_endif(self):
    def op_checkfinalresult(self): # check stack that remaining element is only "TRUE"
```
---
### 기타 파일 및 디렉토리
### 1. `backup/`
- `transaction_backup.json`, `utxo_backup.json` : 초기 트랜잭션 집합과 UTXO 집합 저장

### 2. `json/`
- `transactions.json`, `UTXOes.json` : 실행엔진이 사용할 트랜잭션과 UTXO 집합

### 3. `utils/`
- `crypto_utils.py` : 해시 및 서명 알고리즘 내장
- `json_utils.py` : json데이터를 다루는 함수 집합

### 4. `init.py`
> `json/`디렉토리 내 파일들을 `backup/`디렉토리 파일 내용으로 덮어씌운다. &rarr; (실행 엔진 실행 전 상태로 돌아간다)