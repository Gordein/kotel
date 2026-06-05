import uuid
from datetime import date

from flask import Blueprint, make_response, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..balances import debts_for
from ..db import SessionLocal
from ..errors import ValidationError
from ..ledger import load_ledger
from ..models import Settlement
from ..money import parse_amount
from ..settlements import create_settlement, soft_delete_settlement

bp = Blueprint("settlement", __name__)


def _ok(target):
    if request.headers.get("HX-Request"):
        resp = make_response("", 204)
        resp.headers["HX-Redirect"] = target
        return resp
    return redirect(target)


@bp.get("/settle")
@require_login
def new():
    s = SessionLocal()
    me = current_user()
    people, pairwise = load_ledger(s)
    owe, _owed = debts_for(pairwise, me.id)
    creditors = [{"id": t["to"], "name": people[t["to"]].name, "amount": f'{t["amount"]:.2f}'}
                 for t in owe]
    return render_template("settle_form.html", creditors=creditors,
                           today=date.today().isoformat())


@bp.post("/settle")
@require_login
def create():
    me = current_user()
    s = SessionLocal()
    form = request.form
    try:
        create_settlement(s, from_person=me.id, to_person=int(form["to_person"]),
                          amount=parse_amount(form.get("amount", "")), method=form.get("method", "cash"),
                          settled_on=date.fromisoformat(form.get("settled_on") or date.today().isoformat()),
                          created_by=me.id, request_id=form.get("request_id") or uuid.uuid4().hex)
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return _ok(url_for("balance.index"))


@bp.post("/settle/<int:settlement_id>/delete")
@require_login
def delete(settlement_id):
    s = SessionLocal()
    st = s.get(Settlement, settlement_id)
    if st and st.created_by_id == current_user().id:
        soft_delete_settlement(s, settlement_id, by=current_user().id)
    return redirect(url_for("balance.index"))
