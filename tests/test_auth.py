from app.auth import current_user, login, reset_pin, set_pin, verify_pin
from app.db import SessionLocal
from app.models import Person


def _seed(app):
    with app.app_context():
        s = SessionLocal()
        sam = Person(name="Сэм", color="#d97757", pin_hash=set_pin("1234"))
        s.add(sam)
        s.commit()
        return sam.id


def test_set_and_verify_pin(app):
    h = set_pin("1234")
    assert verify_pin(h, "1234")
    assert not verify_pin(h, "0000")


def test_login_sets_session(app):
    pid = _seed(app)
    with app.test_request_context():
        from flask import session
        assert login(pid, "1234") is True
        assert session["person_id"] == pid
        assert current_user().id == pid


def test_login_wrong_pin(app):
    pid = _seed(app)
    with app.test_request_context():
        assert login(pid, "9999") is False


def test_reset_pin(app):
    pid = _seed(app)
    with app.app_context():
        reset_pin(pid, "5678")
        s = SessionLocal()
        assert verify_pin(s.get(Person, pid).pin_hash, "5678")
