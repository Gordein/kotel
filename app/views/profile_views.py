from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login, reset_pin
from ..db import SessionLocal
from ..models import Person

bp = Blueprint("profile", __name__)


@bp.get("/profile")
@require_login
def index():
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("profile.html", people=people, active="profile")


@bp.post("/profile/pin")
@require_login
def change_pin():
    reset_pin(current_user().id, request.form["pin"])
    return redirect(url_for("profile.index"))


@bp.post("/profile/reset/<int:person_id>")
@require_login
def reset_other(person_id):
    reset_pin(person_id, request.form.get("pin", "0000"))
    return redirect(url_for("profile.index"))
