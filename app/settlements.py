from datetime import datetime
from decimal import Decimal

from .errors import ValidationError
from .models import Settlement


def create_settlement(session, *, from_person, to_person, amount, method,
                      settled_on, created_by, request_id, note=""):
    existing = session.query(Settlement).filter_by(request_id=request_id).first()
    if existing:
        return existing
    if from_person == to_person:
        raise ValidationError("Нельзя переводить самому себе")
    if amount <= Decimal("0"):
        raise ValidationError("Сумма должна быть больше 0")
    st = Settlement(from_person_id=from_person, to_person_id=to_person, amount=amount,
                    method=method, settled_on=settled_on, created_by_id=created_by,
                    note=note, version=1, request_id=request_id)
    session.add(st)
    session.commit()
    return st


def soft_delete_settlement(session, settlement_id, *, by):
    st = session.get(Settlement, settlement_id)
    if st and st.deleted_at is None:
        st.deleted_at = datetime.now()
        session.commit()
    return st
