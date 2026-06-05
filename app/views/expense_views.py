from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..db import SessionLocal
from ..errors import ValidationError
from ..expenses import create_expense
from ..models import Person, Template
from ..money import parse_amount, split_equal
from ..templates_svc import instantiate_template

bp = Blueprint("expense", __name__)

CATEGORIES = ["Квартира", "Продукты", "Хозтовары", "Связь", "Другое"]


@bp.get("/expense/new")
@require_login
def new():
    s = SessionLocal()
    people = s.query(Person).order_by(Person.id).all()
    templates = s.query(Template).filter_by(active=True).all()
    return render_template("expense_form.html", people=people, templates=templates,
                           categories=CATEGORIES, today=date.today().isoformat(), active="add")


@bp.post("/expense")
@require_login
def create():
    s = SessionLocal()
    me = current_user()
    form = request.form
    try:
        amount = parse_amount(form["amount"])
        payer_id = int(form.get("payer_id") or me.id)
        participants = [int(x) for x in form.getlist("participant")]
        if not participants:
            raise ValidationError("Выбери хотя бы одного участника")
        amounts = split_equal(amount, len(participants))
        shares = {pid: amt for pid, amt in zip(participants, amounts)}
        create_expense(s, created_by=me.id, title=(form.get("title") or "").strip() or "Без названия",
                       category=form.get("category", "Другое"),
                       spent_on=date.fromisoformat(form.get("spent_on") or date.today().isoformat()),
                       payers={payer_id: amount}, shares=shares,
                       request_id=form["request_id"])
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return redirect(url_for("feed.index"))


@bp.post("/expense/from-template/<int:template_id>")
@require_login
def from_template(template_id):
    s = SessionLocal()
    today = date.today()
    try:
        instantiate_template(s, template_id=template_id, year=today.year, month=today.month,
                             by=current_user().id)
    except ValidationError as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return redirect(url_for("feed.index"))
