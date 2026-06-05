import pytest

from app.auth import change_pin, current_user, login, set_pin, verify_pin
from app.db import SessionLocal
from app.errors import ValidationError
from app.models import Person


def _seed(app, pins=(("Сэм", "111"), ("Люда", "222"))):
    with app.app_context():
        s = SessionLocal()
        for name, pin in pins:
            s.add(Person(name=name, color="#888", pin_hash=set_pin(pin)))
        s.commit()
        return {p.name: p.id for p in s.query(Person).all()}


def test_set_and_verify_pin(app):
    h = set_pin("111")
    assert verify_pin(h, "111")
    assert not verify_pin(h, "000")


def test_login_by_pin_alone(app):
    ids = _seed(app)
    with app.test_request_context():
        from flask import session
        person = login("222")
        assert person is not None and person.name == "Люда"
        assert session["person_id"] == ids["Люда"]
        assert current_user().id == ids["Люда"]


def test_login_wrong_pin(app):
    _seed(app)
    with app.test_request_context():
        assert login("999") is None
        assert login("") is None


def test_change_pin(app):
    ids = _seed(app)
    with app.app_context():
        change_pin(ids["Сэм"], "555")
        s = SessionLocal()
        assert verify_pin(s.get(Person, ids["Сэм"]).pin_hash, "555")


def test_change_pin_rejects_duplicate(app):
    ids = _seed(app)
    with app.app_context():
        with pytest.raises(ValidationError):
            change_pin(ids["Сэм"], "222")  # already Luda's PIN
