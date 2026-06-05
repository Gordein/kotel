from datetime import datetime
from decimal import Decimal

from .errors import ValidationError, VersionConflict
from .models import Expense, ExpensePayer, ExpenseShare


def _validate(payers: dict, shares: dict) -> Decimal:
    total = sum(payers.values(), Decimal("0"))
    if total <= 0:
        raise ValidationError("Сумма должна быть больше 0")
    if not payers:
        raise ValidationError("Нужен хотя бы один плательщик")
    if not shares:
        raise ValidationError("Нужен хотя бы один участник")
    if sum(shares.values(), Decimal("0")) != total:
        raise ValidationError("Доли не сходятся с суммой")
    return total


def create_expense(session, *, created_by, title, category, spent_on,
                   payers, shares, request_id, note=""):
    existing = session.query(Expense).filter_by(request_id=request_id).first()
    if existing:
        return existing  # idempotent: same request_id never duplicates
    total = _validate(payers, shares)
    exp = Expense(title=title, category=category, amount=total, spent_on=spent_on,
                  note=note, created_by_id=created_by, version=1, request_id=request_id)
    session.add(exp)
    session.flush()
    for pid, amt in payers.items():
        session.add(ExpensePayer(expense_id=exp.id, person_id=pid, amount=amt))
    for pid, amt in shares.items():
        session.add(ExpenseShare(expense_id=exp.id, person_id=pid, amount=amt))
    session.commit()
    return exp


def update_expense(session, *, expense_id, expected_version, by, title, category,
                   spent_on, payers, shares, note=""):
    total = _validate(payers, shares)
    # Optimistic lock: only updates if version still matches what the editor loaded.
    updated = (session.query(Expense)
               .filter_by(id=expense_id, version=expected_version, deleted_at=None)
               .update({"title": title, "category": category, "amount": total,
                        "spent_on": spent_on, "note": note,
                        "version": expected_version + 1},
                       synchronize_session=False))
    if updated == 0:
        session.rollback()
        raise VersionConflict("Запись только что изменили — обнови и попробуй снова")
    session.query(ExpensePayer).filter_by(expense_id=expense_id).delete()
    session.query(ExpenseShare).filter_by(expense_id=expense_id).delete()
    for pid, amt in payers.items():
        session.add(ExpensePayer(expense_id=expense_id, person_id=pid, amount=amt))
    for pid, amt in shares.items():
        session.add(ExpenseShare(expense_id=expense_id, person_id=pid, amount=amt))
    session.commit()
    session.expire_all()
    return session.get(Expense, expense_id)


def soft_delete_expense(session, expense_id, *, by):
    exp = session.get(Expense, expense_id)
    if exp and exp.deleted_at is None:
        exp.deleted_at = datetime.now()
        session.commit()
    return exp
