import uuid
from datetime import date

from flask import Blueprint, make_response, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..db import SessionLocal
from ..errors import ValidationError
from ..expenses import create_expense, soft_delete_expense
from ..models import Expense
from ..money import parse_amount, split_equal

bp = Blueprint("expense", __name__)


def _ok(target):
    """HTMX navigates via HX-Redirect; plain POST falls back to a redirect."""
    if request.headers.get("HX-Request"):
        resp = make_response("", 204)
        resp.headers["HX-Redirect"] = target
        return resp
    return redirect(target)


@bp.post("/expense")
@require_login
def create():
    s = SessionLocal()
    me = current_user()
    form = request.form
    try:
        amount = parse_amount(form.get("amount", ""))
        participants = [int(x) for x in form.getlist("participant")]
        if not participants:
            raise ValidationError("Выбери, на кого делить")
        amounts = split_equal(amount, len(participants))
        shares = {pid: amt for pid, amt in zip(participants, amounts)}
        # payer is always the current user — each person records what THEY paid
        create_expense(s, created_by=me.id, title=(form.get("title") or "").strip() or "Без названия",
                       category=form.get("category", "Другое"),
                       spent_on=date.fromisoformat(form.get("spent_on") or date.today().isoformat()),
                       payers={me.id: amount}, shares=shares, note=(form.get("note") or "").strip(),
                       request_id=form.get("request_id") or uuid.uuid4().hex)
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return _ok(url_for("balance.index"))


@bp.post("/expense/<int:expense_id>/delete")
@require_login
def delete(expense_id):
    s = SessionLocal()
    exp = s.get(Expense, expense_id)
    if exp and exp.created_by_id == current_user().id:  # only your own
        soft_delete_expense(s, expense_id, by=current_user().id)
    return redirect(url_for("balance.index"))
