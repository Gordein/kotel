import json
from datetime import date
from decimal import Decimal

from .errors import ValidationError
from .expenses import create_expense
from .models import Expense, Person, Template


def _name_to_id(session):
    return {p.name: p.id for p in session.query(Person).all()}


def _month_bounds(year, month):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def instantiate_template(session, *, template_id, year, month, by):
    t = session.get(Template, template_id)
    if not t:
        raise ValidationError("Шаблон не найден")
    start, end = _month_bounds(year, month)
    exists = (session.query(Expense)
              .filter(Expense.template_id == template_id, Expense.deleted_at.is_(None),
                      Expense.spent_on >= start, Expense.spent_on < end)
              .first())
    if exists:
        raise ValidationError(f"{t.title} за {month:02d}.{year} уже добавлена")
    name_id = _name_to_id(session)
    payers = {name_id[n]: Decimal(v) for n, v in json.loads(t.default_payers).items()}
    shares = {name_id[n]: Decimal(v) for n, v in json.loads(t.default_shares).items()}
    exp = create_expense(session, created_by=by, title=f"{t.title} {month:02d}.{year}",
                         category=t.category, spent_on=start, payers=payers, shares=shares,
                         note=t.note, request_id=f"tpl-{template_id}-{year}-{month:02d}")
    exp.template_id = template_id
    session.commit()
    return exp


def pending_templates(session, year, month):
    """Active templates not yet added for this month (for the subtle rent prompt)."""
    start, end = _month_bounds(year, month)
    out = []
    for t in session.query(Template).filter_by(active=True).all():
        exists = (session.query(Expense)
                  .filter(Expense.template_id == t.id, Expense.deleted_at.is_(None),
                          Expense.spent_on >= start, Expense.spent_on < end)
                  .first())
        if not exists:
            out.append({"id": t.id, "title": t.title})
    return out
