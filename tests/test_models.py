from datetime import date
from decimal import Decimal

from app.db import SessionLocal
from app.models import Expense, ExpensePayer, ExpenseShare, Person


def test_person_and_expense_roundtrip(app):
    with app.app_context():
        s = SessionLocal()
        sam = Person(name="Сэм", color="#d97757", pin_hash="x")
        s.add(sam)
        s.flush()
        exp = Expense(title="Продукты", category="Продукты", amount=Decimal("30.00"),
                      spent_on=date(2026, 6, 5), created_by_id=sam.id, version=1,
                      request_id="r1")
        s.add(exp)
        s.flush()
        s.add(ExpensePayer(expense_id=exp.id, person_id=sam.id, amount=Decimal("30.00")))
        s.add(ExpenseShare(expense_id=exp.id, person_id=sam.id, amount=Decimal("30.00")))
        s.commit()
        loaded = s.get(Expense, exp.id)
        assert loaded.amount == Decimal("30.00")
        assert len(loaded.payers) == 1
        assert loaded.payers[0].amount == Decimal("30.00")
        assert loaded.deleted_at is None
        assert loaded.created_at is not None
