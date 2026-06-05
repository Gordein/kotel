from datetime import date
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.errors import VersionConflict
from app.expenses import create_expense, update_expense
from app.models import Person

D = Decimal


def _people(app):
    with app.app_context():
        s = SessionLocal()
        ppl = [Person(name=n, color="#888", pin_hash="x") for n in ("Сэм", "Люда", "Микита")]
        s.add_all(ppl)
        s.commit()
        return [p.id for p in ppl]


def test_optimistic_lock_blocks_stale_update(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        exp = create_expense(s, created_by=sam, title="X", category="Другое",
                             spent_on=date(2026, 6, 5),
                             payers={sam: D("30.00")},
                             shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")},
                             request_id="c-1")
        stale_version = exp.version  # both editors loaded version 1

        # First editor wins
        update_expense(s, expense_id=exp.id, expected_version=stale_version, by=lyuda,
                       title="X edited", category="Другое", spent_on=date(2026, 6, 5),
                       payers={sam: D("30.00")},
                       shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")})

        # Second editor with the same stale version must be rejected
        with pytest.raises(VersionConflict):
            update_expense(s, expense_id=exp.id, expected_version=stale_version, by=mikita,
                           title="X clobber", category="Другое", spent_on=date(2026, 6, 5),
                           payers={sam: D("30.00")},
                           shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")})
