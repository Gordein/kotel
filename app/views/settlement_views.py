from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..db import SessionLocal
from ..errors import ValidationError
from ..models import Person
from ..money import parse_amount
from ..settlements import create_settlement

bp = Blueprint("settlement", __name__)


@bp.get("/settle")
@require_login
def new():
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("settle_form.html", people=people, active="balance",
                           today=date.today().isoformat())


@bp.post("/settle")
@require_login
def create():
    me = current_user()
    s = SessionLocal()
    form = request.form
    try:
        create_settlement(s, from_person=me.id, to_person=int(form["to_person"]),
                          amount=parse_amount(form["amount"]), method=form.get("method", "cash"),
                          settled_on=date.fromisoformat(form.get("settled_on") or date.today().isoformat()),
                          created_by=me.id, request_id=form["request_id"])
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return redirect(url_for("balance.index"))
