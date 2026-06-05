from datetime import date, datetime

from flask import Blueprint, render_template, request

from ..auth import current_user, require_login
from ..balances import debts_for
from ..constants import CATEGORIES, RU_MONTHS
from ..db import SessionLocal
from ..feed import build_feed, group_by_month
from ..ledger import activity_count, load_ledger
from ..models import Person, _utcnow

bp = Blueprint("balance", __name__)


def _debts(s, me):
    people, pairwise = load_ledger(s)
    owe, owed = debts_for(pairwise, me.id)
    return people, owe, owed


def _view(s, args, today):
    """Filter the feed by person + (search OR a single month). Returns a view dict."""
    items = build_feed(s)
    person = args.get("person", type=int)
    if person:
        items = [it for it in items if it["actor_id"] == person]

    q = (args.get("q") or "").strip()
    if q:
        ql = q.lower()
        shown = [it for it in items
                 if ql in (it.get("title", "") + " " + it.get("note", "")).lower()]
        return {"groups": group_by_month(shown), "person": person, "q": q,
                "month": "", "nav": None}

    months = []
    for it in items:
        key = (it["on_date"].year, it["on_date"].month)
        if key not in months:
            months.append(key)

    sel = (today.year, today.month)
    if args.get("month"):
        try:
            y, m = args["month"].split("-")
            sel = (int(y), int(m))
        except (ValueError, KeyError):
            pass

    shown = [it for it in items if (it["on_date"].year, it["on_date"].month) == sel]
    older = [mm for mm in months if mm < sel]
    newer = [mm for mm in months if mm > sel]
    prev = max(older) if older else None
    nxt = min(newer) if newer else None
    nav = {"label": f"{RU_MONTHS[sel[1]]} {sel[0]}",
           "prev": f"{prev[0]}-{prev[1]:02d}" if prev else "",
           "next": f"{nxt[0]}-{nxt[1]:02d}" if nxt else ""}
    return {"groups": group_by_month(shown), "person": person, "q": "",
            "month": f"{sel[0]}-{sel[1]:02d}", "nav": nav}


@bp.get("/")
@require_login
def index():
    s = SessionLocal()
    me = current_user()
    today = date.today()
    people, owe, owed = _debts(s, me)
    view = _view(s, request.args, today)
    loaded_at = _utcnow()
    return render_template(
        "home.html",
        people=people, owe=owe, owed=owed, view=view, groups=view["groups"],
        people_list=s.query(Person).order_by(Person.id).all(),
        categories=CATEGORIES, today=today.isoformat(), has_activity=activity_count(s) > 0,
        new_after=loaded_at, loaded_at=loaded_at.isoformat(),
    )


@bp.get("/partials/home")
@require_login
def home_dynamic():
    """Polled every 15s — live balance + filtered feed, dot on items added since load."""
    s = SessionLocal()
    me = current_user()
    today = date.today()
    people, owe, owed = _debts(s, me)
    view = _view(s, request.args, today)
    since = request.args.get("since", "")
    new_after = datetime.fromisoformat(since) if since else _utcnow()
    return render_template("partials/home_dynamic.html", people=people, owe=owe, owed=owed,
                           groups=view["groups"], new_after=new_after)
