from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import login, logout

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_form():
    return render_template("login.html")


@bp.post("/login")
def do_login():
    if login(request.form.get("pin", "")):
        return redirect(url_for("balance.index"))
    return render_template("login.html", error="Неверный PIN"), 401


@bp.post("/logout")
def do_logout():
    logout()
    return redirect(url_for("auth.login_form"))
