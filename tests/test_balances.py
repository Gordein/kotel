from decimal import Decimal

from app.balances import compute_balances, suggest_transfers

D = Decimal


def test_rent_case():
    # Lyuda & Mikita each paid 2600; split Sam 1900 / Lyuda 1900 / Mikita 1400
    expenses = [{
        "payers": {"lyuda": D("2600"), "mikita": D("2600")},
        "shares": {"sam": D("1900"), "lyuda": D("1900"), "mikita": D("1400")},
    }]
    net = compute_balances(expenses, [])
    assert net["sam"] == D("-1900")
    assert net["lyuda"] == D("700")
    assert net["mikita"] == D("1200")
    assert sum(net.values()) == D("0")


def test_settlement_reduces_debt():
    expenses = [{"payers": {"lyuda": D("700")}, "shares": {"sam": D("700")}}]
    settlements = [{"from": "sam", "to": "lyuda", "amount": D("700")}]
    net = compute_balances(expenses, settlements)
    assert net["sam"] == D("0")
    assert net["lyuda"] == D("0")


def test_suggest_transfers_settles_to_zero():
    net = {"sam": D("-1900"), "lyuda": D("700"), "mikita": D("1200")}
    transfers = suggest_transfers(net)
    assert {(t["from"], t["to"], t["amount"]) for t in transfers} == {
        ("sam", "mikita", D("1200")),
        ("sam", "lyuda", D("700")),
    }
    after = dict(net)
    for t in transfers:
        after[t["from"]] += t["amount"]
        after[t["to"]] -= t["amount"]
    assert all(v == D("0") for v in after.values())
