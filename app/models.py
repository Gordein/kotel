from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

Money = Numeric(12, 2, asdecimal=True)


class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    color: Mapped[str] = mapped_column(String(9), default="#888888")
    pin_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), default="Другое")
    amount: Mapped[Decimal] = mapped_column(Money)
    spent_on: Mapped[date] = mapped_column()
    note: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    template_id: Mapped[int | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(16))  # expense | settlement
    target_id: Mapped[int] = mapped_column()
    author_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Template(Base):
    __tablename__ = "templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), default="Квартира (аренда)")
    default_payers: Mapped[str] = mapped_column(Text)  # JSON: {"name": "amount"}
    default_shares: Mapped[str] = mapped_column(Text)   # JSON: {"name": "amount"}
    note: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(default=True)
