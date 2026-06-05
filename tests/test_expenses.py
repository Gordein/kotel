from datetime import date
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.errors import ValidationError
from app.expenses import create_expense, soft_delete_expense
from app.models import Expense, ExpenseShare, Person

D = Decimal


def _people(app):
    with app.app_context():
        s = SessionLocal()
        ppl = [Person(name=n, color="#888", pin_hash="x") for n in ("Сэм", "Люда", "Микита")]
        s.add_all(ppl)
        s.commit()
        return [p.id for p in ppl]


def test_create_expense_persists_lines(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        exp = create_expense(s, created_by=sam, title="Продукты", category="Продукты",
                             spent_on=date(2026, 6, 5),
                             payers={sam: D("30.00")},
                             shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")},
                             request_id="r-1")
        assert exp.amount == D("30.00")
        assert s.query(ExpenseShare).filter_by(expense_id=exp.id).count() == 3


def test_idempotent_request_id(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        kw = dict(created_by=sam, title="X", category="Другое", spent_on=date(2026, 6, 5),
                  payers={sam: D("9.00")}, shares={sam: D("9.00")}, request_id="dup")
        a = create_expense(s, **kw)
        b = create_expense(s, **kw)
        assert a.id == b.id
        assert s.query(Expense).count() == 1


def test_rejects_shares_not_matching_total(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_expense(s, created_by=sam, title="X", category="Другое",
                           spent_on=date(2026, 6, 5),
                           payers={sam: D("30.00")},
                           shares={sam: D("10.00")}, request_id="r-2")


def test_rejects_empty_participants(app):
    sam, *_ = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_expense(s, created_by=sam, title="X", category="Другое",
                           spent_on=date(2026, 6, 5),
                           payers={sam: D("5.00")}, shares={}, request_id="r-3")


def test_soft_delete_keeps_row(app):
    sam, *_ = _people(app)
    with app.app_context():
        s = SessionLocal()
        exp = create_expense(s, created_by=sam, title="X", category="Другое",
                             spent_on=date(2026, 6, 5),
                             payers={sam: D("5.00")}, shares={sam: D("5.00")}, request_id="r-4")
        soft_delete_expense(s, exp.id, by=sam)
        assert s.get(Expense, exp.id).deleted_at is not None
