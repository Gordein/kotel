from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

Money = Numeric(12, 2, asdecimal=True)


def _utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no tz); displayed in Europe/Warsaw via the `dt` filter."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    color: Mapped[str] = mapped_column(String(9), default="#888888")
    pin_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), default="Другое")
    amount: Mapped[Decimal] = mapped_column(Money)
    spent_on: Mapped[date] = mapped_column()
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    version: Mapped[int] = mapped_column(default=1)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    payers: Mapped[list["ExpensePayer"]] = relationship(cascade="all, delete-orphan")
    shares: Mapped[list["ExpenseShare"]] = relationship(cascade="all, delete-orphan")


class ExpensePayer(Base):
    __tablename__ = "expense_payers"
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    amount: Mapped[Decimal] = mapped_column(Money)


class ExpenseShare(Base):
    __tablename__ = "expense_shares"
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    amount: Mapped[Decimal] = mapped_column(Money)


class Settlement(Base):
    __tablename__ = "settlements"
    id: Mapped[int] = mapped_column(primary_key=True)
    from_person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    to_person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    amount: Mapped[Decimal] = mapped_column(Money)
    method: Mapped[str] = mapped_column(String(16), default="cash")  # cash | transfer
    settled_on: Mapped[date] = mapped_column()
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    version: Mapped[int] = mapped_column(default=1)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
