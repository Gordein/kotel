from decimal import Decimal

from app.balances import compute_pairwise, debts_for

D = Decimal


def test_single_payer_charges_each_other_to_payer():
    e = [{"payers": {"luda": D("60")}, "shares": {"sam": D("20"), "luda": D("20"), "mikita": D("20")}}]
    pw = compute_pairwise(e, [])
    # both others owe the payer — this is the bug we fixed
    assert pw[("sam", "luda")] == D("20.00")
    assert pw[("mikita", "luda")] == D("20.00")
    assert ("luda", "sam") not in pw


def test_excluded_person_is_not_charged():
    e = [{"payers": {"luda": D("60")}, "shares": {"luda": D("30"), "mikita": D("30")}}]
    pw = compute_pairwise(e, [])
    assert pw[("mikita", "luda")] == D("30.00")
    assert ("sam", "luda") not in pw


def test_settlement_clears_debt():
    e = [{"payers": {"luda": D("60")}, "shares": {"sam": D("60")}}]
    pw = compute_pairwise(e, [{"from": "sam", "to": "luda", "amount": D("60")}])
    assert pw == {}


def test_rent_pairwise():
    e = [{"payers": {"luda": D("2600"), "mikita": D("2600")},
          "shares": {"sam": D("1900"), "luda": D("1900"), "mikita": D("1400")}}]
    pw = compute_pairwise(e, [])
    # Sam reimburses each payer their exact overpayment; no Luda<->Mikita debt
    assert pw[("sam", "luda")] == D("700.00")
    assert pw[("sam", "mikita")] == D("1200.00")
    assert ("luda", "mikita") not in pw
    assert ("mikita", "luda") not in pw


def test_debts_for_perspective():
    pw = {("sam", "luda"): D("20"), ("mikita", "luda"): D("30")}
    owe, owed = debts_for(pw, "luda")
    assert owe == []
    assert {d["from"] for d in owed} == {"sam", "mikita"}
    owe2, _ = debts_for(pw, "sam")
    assert owe2 == [{"to": "luda", "amount": D("20")}]
