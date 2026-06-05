from datetime import date, datetime

from flask import Blueprint, render_template, request

from ..auth import current_user, require_login
from ..constants import CATEGORIES
from ..db import SessionLocal
from ..feed import build_feed, group_by_month
from ..ledger import load_ledger
from ..models import Person, _utcnow
from ..templates_svc import pending_templates

bp = Blueprint("balance", __name__)


def _debts(s, me):
    people, _net, transfers = load_ledger(s)
    owe = [t for t in transfers if t["from"] == me.id]
    owed = [t for t in transfers if t["to"] == me.id]
    return people, owe, owed


@bp.get("/")
@require_login
def index():
    s = SessionLocal()
    me = current_user()
    today = date.today()
    people, owe, owed = _debts(s, me)
    loaded_at = _utcnow()
    return render_template(
        "home.html",
        people=people, owe=owe, owed=owed,
        people_list=s.query(Person).order_by(Person.id).all(),
        categories=CATEGORIES, pending=pending_templates(s, today.year, today.month),
        today=today.isoformat(),
        groups=group_by_month(build_feed(s)), new_after=loaded_at,
        loaded_at=loaded_at.isoformat(),
    )


@bp.get("/partials/home")
@require_login
def home_dynamic():
    """Polled every 15s — live balance + feed, with a dot on items added since load."""
    s = SessionLocal()
    me = current_user()
    people, owe, owed = _debts(s, me)
    since = request.args.get("since", "")
    new_after = datetime.fromisoformat(since) if since else _utcnow()
    return render_template("partials/home_dynamic.html",
                           people=people, owe=owe, owed=owed,
                           groups=group_by_month(build_feed(s)), new_after=new_after)
