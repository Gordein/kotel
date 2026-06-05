from datetime import date
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.errors import ValidationError
from app.models import Person
from app.settlements import create_settlement

D = Decimal


def _people(app):
    with app.app_context():
        s = SessionLocal()
        ppl = [Person(name=n, color="#888", pin_hash="x") for n in ("Сэм", "Люда")]
        s.add_all(ppl)
        s.commit()
        return [p.id for p in ppl]


def test_create_settlement(app):
    sam, lyuda = _people(app)
    with app.app_context():
        s = SessionLocal()
        st = create_settlement(s, from_person=sam, to_person=lyuda, amount=D("700.00"),
                               method="cash", settled_on=date(2026, 6, 5),
                               created_by=sam, request_id="s-1")
        assert st.amount == D("700.00")


def test_reject_self_settlement(app):
    sam, lyuda = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_settlement(s, from_person=sam, to_person=sam, amount=D("10.00"),
                              method="cash", settled_on=date(2026, 6, 5),
                              created_by=sam, request_id="s-2")


def test_reject_non_positive(app):
    sam, lyuda = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_settlement(s, from_person=sam, to_person=lyuda, amount=D("0.00"),
                              method="cash", settled_on=date(2026, 6, 5),
                              created_by=sam, request_id="s-3")
