from collections import defaultdict
from decimal import Decimal


def compute_pairwise(expenses, settlements):
    """Direct pairwise debts (no rerouting). Returns {(debtor, creditor): Decimal > 0}.

    Each participant owes the payer(s) their share, split across payers in proportion
    to how much each paid. Settlements reduce the debtor's debt to that creditor directly.
    """
    raw = defaultdict(lambda: Decimal("0"))
    for e in expenses:
        payers = e["payers"]
        total = sum(payers.values(), Decimal("0"))
        if total <= 0:
            continue
        for part, share in e["shares"].items():
            for payer, paid in payers.items():
                if part == payer:
                    continue
                raw[(part, payer)] += share * paid / total
    for st in settlements:
        raw[(st["from"], st["to"])] -= st["amount"]

    result = {}
    for a, b in {tuple(sorted(k)) for k in raw}:
        net = (raw[(a, b)] - raw[(b, a)]).quantize(Decimal("0.01"))
        if net > 0:
            result[(a, b)] = net
        elif net < 0:
            result[(b, a)] = -net
    return result


def debts_for(pairwise, me):
    """For person `me`: who they owe and who owes them (sorted by amount, desc)."""
    owe = sorted(({"to": b, "amount": amt} for (a, b), amt in pairwise.items() if a == me),
                 key=lambda x: x["amount"], reverse=True)
    owed = sorted(({"from": a, "amount": amt} for (a, b), amt in pairwise.items() if b == me),
                  key=lambda x: x["amount"], reverse=True)
    return owe, owed
