from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import login, logout
from ..db import SessionLocal
from ..models import Person

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_form():
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("login.html", people=people)


@bp.post("/login")
def do_login():
    pid = int(request.form["person_id"])
    if login(pid, request.form.get("pin", "")):
        return redirect(url_for("balance.index"))
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("login.html", people=people, error="Неверный PIN"), 401


@bp.post("/logout")
def do_logout():
    logout()
    return redirect(url_for("auth.login_form"))
