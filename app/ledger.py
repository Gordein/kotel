from .balances import compute_balances, suggest_transfers
from .models import Expense, ExpensePayer, ExpenseShare, Person, Settlement


def load_ledger(s):
    """Load people + current net balances + suggested transfers from the DB.

    Single source for both the balance screen and the settle screen.
    """
    people = {p.id: p for p in s.query(Person).all()}
    expenses = []
    for e in s.query(Expense).filter_by(deleted_at=None).all():
        payers = {p.person_id: p.amount for p in s.query(ExpensePayer).filter_by(expense_id=e.id)}
        shares = {p.person_id: p.amount for p in s.query(ExpenseShare).filter_by(expense_id=e.id)}
        expenses.append({"payers": payers, "shares": shares})
    settlements = [{"from": x.from_person_id, "to": x.to_person_id, "amount": x.amount}
                   for x in s.query(Settlement).filter_by(deleted_at=None).all()]
    net = compute_balances(expenses, settlements)
    return people, net, suggest_transfers(net)
