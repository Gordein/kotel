import click
from flask.cli import with_appcontext

from .auth import set_pin
from .db import Base, SessionLocal, get_engine
from .models import Person

# name, color, default PIN. Order = seed order on a fresh DB.
FLATMATES = [
    ("Сэм", "#b07a5e", "111"),
    ("Люда", "#6f88a4", "222"),
    ("Мiкiта", "#7d9a72", "333"),
    ("Наташа", "#a07a9a", "444"),
]


def ensure_people(s):
    """Idempotent: add missing flatmates, apply one-time renames. Runs on every app start.

    Late joiners (Наташа) are only added — existing expenses keep their shares,
    so balances before they joined are unchanged.
    """
    old = s.query(Person).filter_by(name="Микита").first()  # one-time rename on existing DBs
    if old and not s.query(Person).filter_by(name="Мiкiта").first():
        old.name = "Мiкiта"
    existing = {p.name for p in s.query(Person).all()}
    for name, color, pin in FLATMATES:
        if name not in existing:
            s.add(Person(name=name, color=color, pin_hash=set_pin(pin)))
    s.commit()


@click.command("init-db")
@with_appcontext
def init_db():
    """Create tables, seed the flatmates (idempotent)."""
    Base.metadata.create_all(get_engine())
    ensure_people(SessionLocal())
    click.echo("DB ready. PINs -> Sam:111  Luda:222  Mikita:333  Natasha:444")
