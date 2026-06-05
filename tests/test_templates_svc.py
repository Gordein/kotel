import json
from decimal import Decimal

from app.db import SessionLocal
from app.errors import ValidationError
from app.models import Person, Template
from app.templates_svc import instantiate_template

D = Decimal


def _seed_rent(app):
    with app.app_context():
        s = SessionLocal()
        names = {}
        for n, c in (("Сэм", "#d97757"), ("Люда", "#6a9bcc"), ("Микита", "#7faa6e")):
            p = Person(name=n, color=c, pin_hash="x")
            s.add(p)
            s.flush()
            names[n] = p.id
        t = Template(title="Аренда", category="Квартира (аренда)",
                     default_payers=json.dumps({"Люда": "2600", "Микита": "2600"}),
                     default_shares=json.dumps({"Сэм": "1900", "Люда": "1900", "Микита": "1400"}),
                     note="переводы Михалу")
        s.add(t)
        s.commit()
        return t.id, names


def test_instantiate_rent_creates_expense(app):
    tid, names = _seed_rent(app)
    with app.app_context():
        s = SessionLocal()
        exp = instantiate_template(s, template_id=tid, year=2026, month=6, by=names["Сэм"])
        assert exp.amount == D("5200")
        payers = {p.person_id: p.amount for p in exp.payers}
        assert payers[names["Люда"]] == D("2600")


def test_duplicate_month_guard(app):
    tid, names = _seed_rent(app)
    with app.app_context():
        s = SessionLocal()
        instantiate_template(s, template_id=tid, year=2026, month=6, by=names["Сэм"])
        try:
            instantiate_template(s, template_id=tid, year=2026, month=6, by=names["Сэм"])
            assert False, "expected ValidationError"
        except ValidationError:
            pass
