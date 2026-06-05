from decimal import Decimal

from .constants import RU_MONTHS
from .models import Expense, Settlement


def build_feed(s, limit=300):
    """Activity feed (derived). Newest-first by operation date, then by add time."""
    items = []
    for e in s.query(Expense).filter_by(deleted_at=None).all():
        items.append({"kind": "expense", "id": e.id, "when": e.created_at, "on_date": e.spent_on,
                      "actor_id": e.created_by_id, "title": e.title, "amount": e.amount,
                      "category": e.category, "note": e.note or ""})
    for st in s.query(Settlement).filter_by(deleted_at=None).all():
        items.append({"kind": "settlement", "id": st.id, "when": st.created_at, "on_date": st.settled_on,
                      "actor_id": st.created_by_id, "from_id": st.from_person_id,
                      "to_id": st.to_person_id, "amount": st.amount, "method": st.method,
                      "note": st.note or ""})
    items.sort(key=lambda x: (x["on_date"], x["when"]), reverse=True)
    return items[:limit]


def group_by_month(items):
    """Group feed items by the operation month. Total = expenses spent that month."""
    groups = []
    cur = None
    for it in items:
        d = it["on_date"]
        key = (d.year, d.month)
        if cur is None or cur["key"] != key:
            cur = {"key": key, "label": f"{RU_MONTHS[d.month]} {d.year}",
                   "total": Decimal("0.00"), "items": []}
            groups.append(cur)
        cur["items"].append(it)
        if it["kind"] == "expense":
            cur["total"] += it["amount"]
    return groups
