import json

import click
from flask.cli import with_appcontext

from .auth import set_pin
from .db import Base, SessionLocal, get_engine
from .models import Person, Template


@click.command("init-db")
@with_appcontext
def init_db():
    """Create tables and seed the three flatmates + rent template."""
    Base.metadata.create_all(get_engine())
    s = SessionLocal()
    if s.query(Person).count() == 0:
        s.add_all([
            Person(name="Сэм", color="#d97757", pin_hash=set_pin("0000")),
            Person(name="Люда", color="#6a9bcc", pin_hash=set_pin("0000")),
            Person(name="Микита", color="#7faa6e", pin_hash=set_pin("0000")),
        ])
    if s.query(Template).count() == 0:
        s.add(Template(
            title="Аренда", category="Квартира (аренда)",
            default_payers=json.dumps({"Люда": "2600", "Микита": "2600"}),
            default_shares=json.dumps({"Сэм": "1900", "Люда": "1900", "Микита": "1400"}),
            note="Люда → Михал: Najem 1900, Opłaty 700\nМикита → Михал: Najem 1900, Opłaty 700",
        ))
    s.commit()
    click.echo("DB initialised. Default PIN for everyone: 0000 (change it on the Profile screen).")
