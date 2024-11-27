import rich
import time

from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from rich.progress import track

# Load transaction vin contents
def vin_load(tx, target=None):
    for tx_input in tx:
        ptxid = tx_input["ptxid"]
        vout = tx_input["vout"]
        scriptSig = tx_input["scriptSig"]
    if not target:
        return ptxid, vout, scriptSig
    elif target=="ptxid":
        return ptxid
    elif target=="vout":
        return vout
    elif target=="scriptSig":
        return scriptSig
    else:
        print("vin_load: Invalidate target")
        return
    

# Load transaction vout contents
def vout_load(tx, target=None):
    if not target:
        return tx["amount"], tx["scriptPubKey"]
    elif target=="amount":
        return tx["amount"]
    elif target=="scriptPubKey":
        return tx["scriptPubKey"]
    else:
        print("vout_load: Invalidate target")
        return
    

# update scriptSig(to make signature)
def scriptSig_update(tx, scriptPubKey):
    for tx_input in tx:
        tx_input["scriptSig"] = scriptPubKey
    
    return tx


# Calculate sum of vout amount
def vout_amount_sum(tx):
    vout_amount_sum = 0
    for tx_output in tx:
        vout_amount_sum += tx_output["amount"]
    
    return vout_amount_sum


# Find utxo in utxo set by ptxid and vout index
def utxo_find(utxoes, ptxid, vout):
    for utxo in utxoes:
        if utxo["ptxid"]==ptxid and utxo["vout"]==vout:
            return utxo
        
    return False


# Load utxo contents
def utxo_load(utxo, target=None):
    amount = utxo["amount"]
    scriptPubKey = utxo["scriptPubKey"]
    if not target:
        return amount, scriptPubKey
    

# Check whether P2SH or not
def pay_typecheck(scriptPubKey):
    script = scriptPubKey.split()

    # P2SH, return 1
    if script[-1] == "EQUALVERIFY":
        return 1
    
    # other return 0
    else:
        return 0
    

    
def tx_print(tx, error=None):
    console = Console()

    rich.print(Panel(f"[bold white]txid: {tx['txid']}[/bold white]", title="transaction", border_style="bold white"))

    for tx_input in tx["vin"]:
        rich.print(f'\t[bold white]input \t\tptxid:[/bold white] {tx_input["ptxid"]}')
        rich.print(f'\t\t\t[bold white]vout:[/bold white] {tx_input["vout"]}')
        scriptSig_text = Text(tx_input["scriptSig"], style="yellow", overflow="ellipsis")
        console.print("\t\t\t[bold white]scriptSig:[/bold white] ", scriptSig_text)

    for idx, tx_output in enumerate(tx["vout"]):
        rich.print(f'\t[bold white]output:{idx} \tamount: [/bold white]{tx_output["amount"]}')
        rich.print(f'\t\t\t[bold white]scriptPubKey:[/bold white] [yellow]{tx_output["scriptPubKey"]}[/yellow]')

    if not error:
        rich.print("[cyan]\tvalidity check: passed[cyan]")
    else:
        rich.print("[red]\tvalidity check: failed[/red]")
        rich.print(f"[red]\t\t\tfailed at [bold italic]{error}[/bold italic][/red]")


def loading_print(wait):
    print()
    print()
    for step in track(range(wait*2), description="Next Transaction Processing..."):
        time.sleep(0.5)
    print()
    print()


def query_tx_print(id, tx, error=None):
    if tx["validity check"]:
        rich.print(Panel(f"[bold white]txid: {tx['txid']}[/bold white]\nvalidity check: [cyan]passed[/cyan]", title=f"transaction{id}", border_style="bold white"))
    else:
        rich.print(Panel(f"[bold white]txid: {tx['txid']}[/bold white]\nvalidity check: [red]failed[/red]", title=f"transaction{id}", border_style="bold white"))
    
    print()
    print()


def query_utxo_print(id, utxo):
    rich.print(Panel(f'[bold white]ptxid: {utxo["ptxid"]}[/bold white]\n[bold white]output index:[/bold white] {utxo["vout"]}\n[bold white]amount:[/bold white] {utxo["amount"]}\n[bold white]locking script:[/bold white] [yellow]{utxo["scriptPubKey"]}[/yellow]', title=f"utxo{id}", border_style="bold white"))
    
    print()
    print()


def utxo_print(utxo, val=None):
    if val=="red":
        rich.print(f"[red]{utxo}[/red]")
    elif val=="cyan":
        rich.print(f"[cyan]{utxo}[/cyan]")