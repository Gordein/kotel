from datetime import datetime

from .errors import ValidationError
from .models import Comment


def add_comment(session, *, target_type, target_id, author_id, text):
    text = (text or "").strip()
    if not text:
        raise ValidationError("Пустой комментарий")
    if target_type not in ("expense", "settlement"):
        raise ValidationError("Неверный тип цели")
    c = Comment(target_type=target_type, target_id=target_id, author_id=author_id, text=text)
    session.add(c)
    session.commit()
    return c


def comments_for(session, target_type, target_id):
    return (session.query(Comment)
            .filter_by(target_type=target_type, target_id=target_id, deleted_at=None)
            .order_by(Comment.created_at.asc()).all())


def soft_delete_comment(session, comment_id, *, by):
    c = session.get(Comment, comment_id)
    if c and c.deleted_at is None:
        c.deleted_at = datetime.now()
        session.commit()
    return c
