from decimal import Decimal

from flask import Blueprint, render_template

from ..auth import current_user, require_login
from ..db import SessionLocal
from ..ledger import load_ledger

bp = Blueprint("balance", __name__)


@bp.get("/")
@require_login
def index():
    s = SessionLocal()
    me = current_user()
    people, net, transfers = load_ledger(s)
    invariant_ok = sum(net.values(), Decimal("0")) == 0
    owe = [t for t in transfers if t["from"] == me.id]
    owed = [t for t in transfers if t["to"] == me.id]
    my_edges = [t for t in transfers if me.id in (t["from"], t["to"])]
    return render_template("balance.html", people=people, owe=owe, owed=owed,
                           my_edges=my_edges, invariant_ok=invariant_ok, active="balance")
