from functools import wraps

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import SessionLocal
from .models import Person


def set_pin(pin: str) -> str:
    return generate_password_hash(pin)


def verify_pin(pin_hash: str, pin: str) -> bool:
    return check_password_hash(pin_hash, pin)


def login(person_id: int, pin: str) -> bool:
    person = SessionLocal().get(Person, person_id)
    if person and verify_pin(person.pin_hash, pin):
        session["person_id"] = person.id
        session.permanent = True
        return True
    return False


def logout():
    session.pop("person_id", None)


def current_user():
    pid = session.get("person_id")
    return SessionLocal().get(Person, pid) if pid else None


def reset_pin(person_id: int, new_pin: str):
    person = SessionLocal().get(Person, person_id)
    person.pin_hash = set_pin(new_pin)
    SessionLocal().commit()


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login_form"))
        return view(*args, **kwargs)
    return wrapped
