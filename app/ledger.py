from .balances import compute_pairwise
from .models import Expense, ExpensePayer, ExpenseShare, Person, Settlement


def load_ledger(s):
    """Load people + pairwise debts {(debtor, creditor): amount} from the DB."""
    people = {p.id: p for p in s.query(Person).all()}
    expenses = []
    for e in s.query(Expense).filter_by(deleted_at=None).all():
        payers = {p.person_id: p.amount for p in s.query(ExpensePayer).filter_by(expense_id=e.id)}
        shares = {p.person_id: p.amount for p in s.query(ExpenseShare).filter_by(expense_id=e.id)}
        expenses.append({"payers": payers, "shares": shares})
    settlements = [{"from": x.from_person_id, "to": x.to_person_id, "amount": x.amount}
                   for x in s.query(Settlement).filter_by(deleted_at=None).all()]
    return people, compute_pairwise(expenses, settlements)


def activity_count(s):
    """Number of live feed items (expenses + settlements). Used to detect new activity."""
    return (s.query(Expense).filter_by(deleted_at=None).count()
            + s.query(Settlement).filter_by(deleted_at=None).count())
