from collections import defaultdict
from decimal import Decimal

ZERO = Decimal("0")


def compute_pairwise(expenses, settlements):
    """Direct pairwise debts. Returns {(debtor, creditor): Decimal > 0}.

    Per expense, net each person (paid - share); underpayers owe overpayers in
    proportion to each overpayer's surplus. This keeps everyday splits symmetric
    (each participant owes the payer their share) AND keeps multi-payer cases like
    rent clean (the underpayer reimburses each overpayer their exact overpayment,
    no spurious debt between the two payers). Settlements reduce a pair directly.
    """
    raw = defaultdict(lambda: Decimal("0"))
    for e in expenses:
        payers, shares = e["payers"], e["shares"]
        people = set(payers) | set(shares)
        net = {p: payers.get(p, ZERO) - shares.get(p, ZERO) for p in people}
        over = {p: v for p, v in net.items() if v > 0}
        under = {p: -v for p, v in net.items() if v < 0}
        total_over = sum(over.values(), ZERO)
        if total_over <= 0:
            continue
        for debtor, deficit in under.items():
            for creditor, surplus in over.items():
                raw[(debtor, creditor)] += deficit * surplus / total_over
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
