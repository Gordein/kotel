from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..comments import add_comment, comments_for
from ..db import SessionLocal
from ..errors import ValidationError
from ..feed import build_feed
from ..models import Person

bp = Blueprint("feed", __name__)


@bp.get("/feed")
@require_login
def index():
    s = SessionLocal()
    people = {p.id: p for p in s.query(Person).all()}
    return render_template("feed.html", items=build_feed(s), people=people, active="feed")


@bp.get("/item/<target_type>/<int:target_id>/comments")
@require_login
def comments(target_type, target_id):
    s = SessionLocal()
    people = {p.id: p for p in s.query(Person).all()}
    return render_template("partials/comments.html", target_type=target_type,
                           target_id=target_id, comments=comments_for(s, target_type, target_id),
                           people=people)


@bp.post("/item/<target_type>/<int:target_id>/comments")
@require_login
def post_comment(target_type, target_id):
    s = SessionLocal()
    try:
        add_comment(s, target_type=target_type, target_id=target_id,
                    author_id=current_user().id, text=request.form.get("text", ""))
    except ValidationError:
        pass
    return redirect(url_for("feed.comments", target_type=target_type, target_id=target_id))
