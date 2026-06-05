from flask import Blueprint, render_template, request

from ..auth import change_pin, current_user, require_login
from ..errors import ValidationError

bp = Blueprint("profile", __name__)


@bp.get("/profile")
@require_login
def index():
    return render_template("profile.html", active="profile")


@bp.post("/profile/pin")
@require_login
def update_pin():
    try:
        change_pin(current_user().id, request.form.get("pin", ""))
        msg = "PIN обновлён"
    except ValidationError as e:
        msg = str(e)
    return render_template("profile.html", active="profile", msg=msg)
