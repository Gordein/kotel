from decimal import Decimal

from flask import Blueprint, render_template

from ..auth import current_user, require_login
from ..balances import compute_balances, suggest_transfers
from ..db import SessionLocal
from ..models import Expense, ExpensePayer, ExpenseShare, Person, Settlement

bp = Blueprint("balance", __name__)


def _load_balances(s):
    people = {p.id: p for p in s.query(Person).all()}
    expenses = []
    for e in s.query(Expense).filter_by(deleted_at=None).all():
        payers = {p.person_id: p.amount for p in s.query(ExpensePayer).filter_by(expense_id=e.id)}
        shares = {p.person_id: p.amount for p in s.query(ExpenseShare).filter_by(expense_id=e.id)}
        expenses.append({"payers": payers, "shares": shares})
    settlements = [{"from": x.from_person_id, "to": x.to_person_id, "amount": x.amount}
                   for x in s.query(Settlement).filter_by(deleted_at=None).all()]
    net = compute_balances(expenses, settlements)
    transfers = suggest_transfers(net)
    return people, net, transfers


@bp.get("/")
@require_login
def index():
    s = SessionLocal()
    me = current_user()
    people, net, transfers = _load_balances(s)
    invariant_ok = sum(net.values(), Decimal("0")) == 0
    owe = [t for t in transfers if t["from"] == me.id]
    owed = [t for t in transfers if t["to"] == me.id]
    return render_template("balance.html", people=people, transfers=transfers,
                           owe=owe, owed=owed, invariant_ok=invariant_ok, active="balance")
