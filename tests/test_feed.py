from datetime import date
from decimal import Decimal

from app.comments import add_comment
from app.db import SessionLocal
from app.expenses import create_expense
from app.feed import build_feed
from app.models import Person

D = Decimal


def test_feed_orders_newest_first_with_comment_counts(app):
    with app.app_context():
        s = SessionLocal()
        sam = Person(name="Сэм", color="#888", pin_hash="x")
        s.add(sam)
        s.commit()
        e = create_expense(s, created_by=sam.id, title="Продукты", category="Продукты",
                           spent_on=date(2026, 6, 5), payers={sam.id: D("9.00")},
                           shares={sam.id: D("9.00")}, request_id="f-1")
        add_comment(s, target_type="expense", target_id=e.id, author_id=sam.id, text="ок")
        feed = build_feed(s)
        assert feed[0]["kind"] == "expense"
        assert feed[0]["comment_count"] == 1
