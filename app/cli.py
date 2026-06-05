import click
from flask.cli import with_appcontext

from .auth import set_pin
from .db import Base, SessionLocal, get_engine
from .models import Person


@click.command("init-db")
@with_appcontext
def init_db():
    """Create tables, seed the three flatmates (idempotent)."""
    Base.metadata.create_all(get_engine())
    s = SessionLocal()
    if s.query(Person).count() == 0:
        s.add_all([
            Person(name="Сэм", color="#b07a5e", pin_hash=set_pin("111")),
            Person(name="Люда", color="#6f88a4", pin_hash=set_pin("222")),
            Person(name="Мiкiта", color="#7d9a72", pin_hash=set_pin("333")),
        ])
    else:
        old = s.query(Person).filter_by(name="Микита").first()  # one-time rename on existing DBs
        if old:
            old.name = "Мiкiта"
    s.commit()
    click.echo("DB ready. PINs -> Sam:111  Luda:222  Mikita:333")
