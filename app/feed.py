from datetime import date

from .models import Comment, Expense, Settlement


def _count(session, target_type, target_id):
    return (session.query(Comment)
            .filter_by(target_type=target_type, target_id=target_id, deleted_at=None).count())


def _first(y, m):
    return date(y, m, 1)


def _next(y, m):
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)


def build_feed(session, *, month=None, limit=100):
    """Return list of feed items (dicts) newest-first.
    Derived from Expense + Settlement (no separate activity table).
    Each item: {kind, id, when, actor_id, ..., comment_count}.
    """
    items = []
    eq = session.query(Expense).filter_by(deleted_at=None)
    sq = session.query(Settlement).filter_by(deleted_at=None)
    if month:
        y, m = month
        eq = eq.filter(Expense.spent_on >= _first(y, m), Expense.spent_on < _next(y, m))
        sq = sq.filter(Settlement.settled_on >= _first(y, m), Settlement.settled_on < _next(y, m))
    for e in eq.all():
        items.append({"kind": "expense", "id": e.id, "when": e.created_at,
                      "actor_id": e.created_by_id, "title": e.title,
                      "amount": e.amount, "category": e.category,
                      "comment_count": _count(session, "expense", e.id)})
    for st in sq.all():
        items.append({"kind": "settlement", "id": st.id, "when": st.created_at,
                      "actor_id": st.created_by_id, "from_id": st.from_person_id,
                      "to_id": st.to_person_id, "amount": st.amount, "method": st.method,
                      "comment_count": _count(session, "settlement", st.id)})
    items.sort(key=lambda x: x["when"], reverse=True)
    return items[:limit]
