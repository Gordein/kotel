from functools import wraps

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import SessionLocal
from .errors import ValidationError
from .models import Person


def set_pin(pin: str) -> str:
    return generate_password_hash(pin)


def verify_pin(pin_hash: str, pin: str) -> bool:
    return check_password_hash(pin_hash, pin)


def login(pin: str):
    """Password-only login: the PIN alone identifies the account.

    Returns the matched Person (and sets the session) or None.
    """
    pin = (pin or "").strip()
    if not pin:
        return None
    for person in SessionLocal().query(Person).order_by(Person.id).all():
        if verify_pin(person.pin_hash, pin):
            session["person_id"] = person.id
            session.permanent = True
            return person
    return None


def logout():
    session.pop("person_id", None)


def current_user():
    pid = session.get("person_id")
    return SessionLocal().get(Person, pid) if pid else None


def change_pin(person_id: int, new_pin: str):
    """Change your own PIN. PINs stay unique so password-only login is unambiguous."""
    new_pin = (new_pin or "").strip()
    if not new_pin:
        raise ValidationError("Пустой PIN")
    s = SessionLocal()
    for other in s.query(Person).filter(Person.id != person_id).all():
        if verify_pin(other.pin_hash, new_pin):
            raise ValidationError("Такой PIN уже занят — выбери другой")
    person = s.get(Person, person_id)
    person.pin_hash = set_pin(new_pin)
    s.commit()


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login_form"))
        return view(*args, **kwargs)
    return wrapped
