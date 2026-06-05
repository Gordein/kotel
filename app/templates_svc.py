import json
from datetime import date
from decimal import Decimal

from .errors import ValidationError
from .expenses import create_expense
from .models import Expense, Person, Template


def _name_to_id(session):
    return {p.name: p.id for p in session.query(Person).all()}


def instantiate_template(session, *, template_id, year, month, by):
    t = session.get(Template, template_id)
    if not t:
        raise ValidationError("Шаблон не найден")
    period_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    exists = (session.query(Expense)
              .filter(Expense.template_id == template_id,
                      Expense.deleted_at.is_(None),
                      Expense.spent_on >= date(year, month, 1),
                      Expense.spent_on < period_end)
              .first())
    if exists:
        raise ValidationError(f"{t.title} за {month:02d}.{year} уже добавлена")
    name_id = _name_to_id(session)
    payers = {name_id[n]: Decimal(v) for n, v in json.loads(t.default_payers).items()}
    shares = {name_id[n]: Decimal(v) for n, v in json.loads(t.default_shares).items()}
    exp = create_expense(session, created_by=by, title=f"{t.title} {month:02d}.{year}",
                         category=t.category, spent_on=date(year, month, 1),
                         payers=payers, shares=shares, note=t.note,
                         request_id=f"tpl-{template_id}-{year}-{month:02d}")
    exp.template_id = template_id
    session.commit()
    return exp
