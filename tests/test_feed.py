from datetime import date
from decimal import Decimal

from app.db import SessionLocal
from app.expenses import create_expense
from app.feed import build_feed, group_by_month
from app.models import Person

D = Decimal


def test_feed_and_month_grouping(app):
    with app.app_context():
        s = SessionLocal()
        sam = Person(name="Сэм", color="#888", pin_hash="x")
        s.add(sam)
        s.commit()
        create_expense(s, created_by=sam.id, title="Продукты", category="Продукты",
                       spent_on=date(2026, 6, 5), payers={sam.id: D("30.00")},
                       shares={sam.id: D("30.00")}, request_id="f-1", note="чек")
        feed = build_feed(s)
        assert feed[0]["kind"] == "expense"
        assert feed[0]["title"] == "Продукты"
        assert feed[0]["note"] == "чек"
        groups = group_by_month(feed)
        assert groups[0]["label"] == "Июнь 2026"
        assert groups[0]["total"] == D("30.00")
