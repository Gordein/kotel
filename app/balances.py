from collections import defaultdict
from decimal import Decimal

ZERO = Decimal("0.00")


def compute_balances(expenses, settlements):
    """expenses: [{"payers": {pid: Decimal}, "shares": {pid: Decimal}}]
    settlements: [{"from": pid, "to": pid, "amount": Decimal}]
    Returns {pid: net Decimal}. net>0 => group owes pid; net<0 => pid owes group.
    """
    net = defaultdict(lambda: Decimal("0"))
    for e in expenses:
        for pid, amt in e["payers"].items():
            net[pid] += amt
        for pid, amt in e["shares"].items():
            net[pid] -= amt
    for s in settlements:
        net[s["from"]] += s["amount"]
        net[s["to"]] -= s["amount"]
    return {pid: bal for pid, bal in net.items()}


def suggest_transfers(net):
    """Greedy min-transfer: largest debtor pays largest creditor."""
    debtors = sorted(([pid, -bal] for pid, bal in net.items() if bal < 0),
                     key=lambda x: x[1], reverse=True)
    creditors = sorted(([pid, bal] for pid, bal in net.items() if bal > 0),
                       key=lambda x: x[1], reverse=True)
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        d, c = debtors[i], creditors[j]
        amt = min(d[1], c[1])
        if amt > 0:
            transfers.append({"from": d[0], "to": c[0], "amount": amt})
        d[1] -= amt
        c[1] -= amt
        if d[1] == 0:
            i += 1
        if c[1] == 0:
            j += 1
    return transfers
