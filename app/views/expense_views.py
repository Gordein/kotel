import uuid
from datetime import date

from flask import Blueprint, make_response, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..constants import CATEGORIES
from ..db import SessionLocal
from ..errors import ValidationError, VersionConflict
from ..expenses import create_expense, soft_delete_expense, update_expense
from ..models import Expense, ExpenseShare, Person
from ..money import parse_amount, split_equal

bp = Blueprint("expense", __name__)


def _ok(target):
    """HTMX navigates via HX-Redirect; plain POST falls back to a redirect."""
    if request.headers.get("HX-Request"):
        resp = make_response("", 204)
        resp.headers["HX-Redirect"] = target
        return resp
    return redirect(target)


def _equal_split(form):
    amount = parse_amount(form.get("amount", ""))
    participants = [int(x) for x in form.getlist("participant")]
    if not participants:
        raise ValidationError("Выбери, на кого делить")
    amounts = split_equal(amount, len(participants))
    return amount, {pid: amt for pid, amt in zip(participants, amounts)}


def _own_expense(s, expense_id, me):
    exp = s.get(Expense, expense_id)
    if not exp or exp.deleted_at is not None or exp.created_by_id != me.id:
        return None
    return exp


@bp.post("/expense")
@require_login
def create():
    s = SessionLocal()
    me = current_user()
    form = request.form
    try:
        amount, shares = _equal_split(form)
        # payer is always the current user — each person records what THEY paid
        create_expense(s, created_by=me.id, title=(form.get("title") or "").strip() or "Без названия",
                       category=form.get("category", "Другое"),
                       spent_on=date.fromisoformat(form.get("spent_on") or date.today().isoformat()),
                       payers={me.id: amount}, shares=shares, note=(form.get("note") or "").strip(),
                       request_id=form.get("request_id") or uuid.uuid4().hex)
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return _ok(url_for("balance.index"))


@bp.get("/expense/<int:expense_id>/edit")
@require_login
def edit(expense_id):
    s = SessionLocal()
    exp = _own_expense(s, expense_id, current_user())
    if not exp:
        return redirect(url_for("balance.index"))
    participants = [sh.person_id for sh in s.query(ExpenseShare).filter_by(expense_id=exp.id)]
    return render_template("edit_form.html", exp=exp, participants=participants,
                           people_list=s.query(Person).order_by(Person.id).all(),
                           categories=CATEGORIES)


@bp.post("/expense/<int:expense_id>/edit")
@require_login
def update(expense_id):
    s = SessionLocal()
    me = current_user()
    form = request.form
    exp = _own_expense(s, expense_id, me)
    if not exp:
        return redirect(url_for("balance.index"))
    try:
        amount, shares = _equal_split(form)
        update_expense(s, expense_id=expense_id, expected_version=int(form.get("version") or 0),
                       by=me.id, title=(form.get("title") or "").strip() or "Без названия",
                       category=form.get("category", "Другое"), spent_on=exp.spent_on,
                       payers={me.id: amount}, shares=shares, note=(form.get("note") or "").strip())
    except VersionConflict:
        return render_template("partials/form_error.html",
                               error="Запись только что изменили — открой её заново."), 409
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return _ok(url_for("balance.index"))


@bp.post("/expense/<int:expense_id>/delete")
@require_login
def delete(expense_id):
    s = SessionLocal()
    me = current_user()
    if _own_expense(s, expense_id, me):  # only your own
        soft_delete_expense(s, expense_id, by=me.id)
    return redirect(url_for("balance.index"))
