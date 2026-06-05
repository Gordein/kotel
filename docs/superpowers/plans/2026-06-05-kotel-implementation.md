# Котёл — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-flat, single-currency (zł) expense-splitter PWA for 3 roommates with profile+PIN identity, payers/shares expenses, derived balances, settlements, comments, templates, and an activity feed — with strong no-lost-data guarantees.

**Architecture:** Flask app factory + SQLAlchemy 2.0 + SQLite (WAL). Pure domain logic (money math, balances) lives in framework-free modules with full test coverage. Records are immutable-ish (soft-delete + version); **balances are computed on read**, never stored, so concurrent writers can't clobber a shared counter. Server-rendered Jinja + HTMX for partial updates + Alpine for tiny interactions. PWA via manifest + service worker.

**Tech Stack:** Python 3.12, Flask, SQLAlchemy 2.0, SQLite (WAL), Werkzeug password hashing (for PINs), pytest, HTMX, Alpine.js, vanilla CSS (Claude-style).

---

## File Structure

```
kotel/
├── app/
│   ├── __init__.py            # app factory, db init, blueprint registration, /healthz
│   ├── config.py              # SECRET_KEY, DB path, timezone
│   ├── db.py                  # engine (WAL pragma), Base, scoped session
│   ├── models.py              # Person, Expense, ExpensePayer, ExpenseShare, Settlement, Comment, Template
│   ├── money.py               # parse/format amounts, equal split w/ remainder (pure)
│   ├── balances.py            # compute_balances, suggest_transfers (pure)
│   ├── errors.py              # VersionConflict, ValidationError
│   ├── auth.py                # login, current_user, require_login, reset_pin
│   ├── expenses.py            # create/update/soft-delete expense (validation, version, idempotency)
│   ├── settlements.py         # create/soft-delete settlement (validation)
│   ├── comments.py            # add/soft-delete comment
│   ├── feed.py                # assemble activity feed (union over records)
│   ├── templates_svc.py       # instantiate template (rent), duplicate-month guard, seed
│   ├── cli.py                 # `flask init-db` (create tables + seed people/templates)
│   ├── views/
│   │   ├── __init__.py
│   │   ├── auth_views.py
│   │   ├── balance_views.py
│   │   ├── feed_views.py
│   │   ├── expense_views.py
│   │   ├── settlement_views.py
│   │   └── profile_views.py
│   ├── templates/             # base.html, login.html, balance.html, feed.html, expense_form.html, partials/
│   └── static/
│       ├── styles.css
│       ├── app.js
│       ├── manifest.webmanifest
│       └── sw.js
├── tests/
│   ├── conftest.py
│   ├── test_money.py
│   ├── test_balances.py
│   ├── test_models.py
│   ├── test_auth.py
│   ├── test_expenses.py
│   ├── test_concurrency.py
│   ├── test_settlements.py
│   ├── test_templates_svc.py
│   └── test_views.py
├── requirements.txt
├── wsgi.py
├── pytest.ini
├── CLAUDE.md
└── README.md
```

**Design boundaries:** `money.py` and `balances.py` are pure (no Flask, no DB) → trivially testable, the correctness core. Services (`expenses.py`, `settlements.py`, `comments.py`, `templates_svc.py`) own all writes + validation + concurrency control; views are thin and call services. Files split by responsibility, each small enough to hold in context.

---

## Task 1: Project scaffold + app factory

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `wsgi.py`, `app/__init__.py`, `app/config.py`, `app/db.py`, `tests/conftest.py`, `tests/test_views.py`

- [ ] **Step 1: requirements.txt**

```
Flask==3.0.3
SQLAlchemy==2.0.31
pytest==8.2.2
waitress==3.0.0
```

- [ ] **Step 2: pytest.ini**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 3: app/config.py**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    DB_PATH = os.environ.get("KOTEL_DB", str(BASE_DIR / "kotel.db"))
    TZ = "Europe/Warsaw"
    TESTING = False
```

- [ ] **Step 4: app/db.py**

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


SessionLocal = scoped_session(sessionmaker(future=True, expire_on_commit=False))
_engine = None


def init_engine(db_path: str):
    global _engine
    url = "sqlite:///:memory:" if db_path == ":memory:" else f"sqlite:///{db_path}"
    _engine = create_engine(url, future=True)

    @event.listens_for(_engine, "connect")
    def _pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    SessionLocal.configure(bind=_engine)
    return _engine


def get_engine():
    return _engine
```

- [ ] **Step 5: app/__init__.py**

```python
from flask import Flask

from .config import Config
from .db import Base, SessionLocal, init_engine


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    engine = init_engine(app.config["DB_PATH"])
    from . import models  # noqa: F401  (register mappers)
    Base.metadata.create_all(engine)

    @app.teardown_appcontext
    def _remove_session(exc=None):
        SessionLocal.remove()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app
```

- [ ] **Step 6: app/models.py (placeholder module so import works)**

```python
# models are added in Task 3; empty for now so `from . import models` succeeds
```

- [ ] **Step 7: wsgi.py**

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=8000, debug=True)
```

- [ ] **Step 8: tests/conftest.py**

```python
import pytest

from app import create_app
from app.config import Config


class TestConfig(Config):
    TESTING = True
    DB_PATH = ":memory:"


@pytest.fixture
def app():
    return create_app(TestConfig)


@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 9: tests/test_views.py (failing test)**

```python
def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}
```

- [ ] **Step 10: Run + verify**

Run: `pip install -r requirements.txt && pytest tests/test_views.py -v`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add -A && git commit -m "feat: project scaffold + Flask app factory with WAL SQLite"
```

---

## Task 2: Money math (pure)

**Files:** Create `app/money.py`, `tests/test_money.py`

- [ ] **Step 1: tests/test_money.py (failing)**

```python
from decimal import Decimal

import pytest

from app.money import format_amount, parse_amount, split_equal


def test_parse_rounds_to_grosze():
    assert parse_amount("33.335") == Decimal("33.34")
    assert parse_amount(5.5) == Decimal("5.50")


def test_parse_rejects_non_positive():
    with pytest.raises(ValueError):
        parse_amount("0")
    with pytest.raises(ValueError):
        parse_amount("-3")


def test_split_equal_distributes_remainder():
    shares = split_equal(Decimal("100.00"), 3)
    assert shares == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert sum(shares) == Decimal("100.00")


def test_split_equal_clean():
    assert split_equal(Decimal("90.00"), 3) == [Decimal("30.00")] * 3


def test_format_amount():
    assert format_amount(Decimal("5.5")) == "5.50"
```

- [ ] **Step 2: Run to verify FAIL**

Run: `pytest tests/test_money.py -v` → FAIL (module missing).

- [ ] **Step 3: app/money.py**

```python
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def parse_amount(value) -> Decimal:
    d = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    if d <= 0:
        raise ValueError("amount must be > 0")
    return d


def format_amount(d: Decimal) -> str:
    return f"{Decimal(d).quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def split_equal(total: Decimal, n: int) -> list[Decimal]:
    if n <= 0:
        raise ValueError("need at least one participant")
    base = (total / n).quantize(CENT, rounding=ROUND_DOWN)
    shares = [base] * n
    remainder = total - base * n
    extra_count = int((remainder / CENT).to_integral_value())
    for i in range(extra_count):
        shares[i] += CENT
    return shares
```

- [ ] **Step 4: Run + verify PASS.** Run: `pytest tests/test_money.py -v`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: money math (parse/format/equal-split with remainder)"
```

---

## Task 3: Data models

**Files:** Modify `app/models.py`; Create `tests/test_models.py`

- [ ] **Step 1: tests/test_models.py (failing)**

```python
from datetime import date
from decimal import Decimal

from app.db import SessionLocal
from app.models import Expense, ExpensePayer, ExpenseShare, Person


def test_person_and_expense_roundtrip(app):
    with app.app_context():
        s = SessionLocal()
        sam = Person(name="Сэм", color="#d97757", pin_hash="x")
        s.add(sam)
        s.flush()
        exp = Expense(title="Продукты", category="Продукты", amount=Decimal("30.00"),
                      spent_on=date(2026, 6, 5), created_by_id=sam.id, version=1,
                      request_id="r1")
        s.add(exp)
        s.flush()
        s.add(ExpensePayer(expense_id=exp.id, person_id=sam.id, amount=Decimal("30.00")))
        s.add(ExpenseShare(expense_id=exp.id, person_id=sam.id, amount=Decimal("30.00")))
        s.commit()
        loaded = s.get(Expense, exp.id)
        assert loaded.amount == Decimal("30.00")
        assert len(loaded.payers) == 1
        assert loaded.payers[0].amount == Decimal("30.00")
        assert loaded.deleted_at is None
```

- [ ] **Step 2: Run to verify FAIL** (`pytest tests/test_models.py -v`).

- [ ] **Step 3: app/models.py**

```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

Money = Numeric(12, 2, asdecimal=True)


class Person(Base):
    __tablename__ = "people"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    color: Mapped[str] = mapped_column(String(9), default="#888888")
    pin_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
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
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Comment(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(16))  # expense | settlement
    target_id: Mapped[int] = mapped_column()
    author_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
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
```

- [ ] **Step 4: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: SQLAlchemy models (people, expenses, payers/shares, settlements, comments, templates)"
```

---

## Task 4: Balances + transfer suggestion (pure)

**Files:** Create `app/balances.py`, `tests/test_balances.py`

- [ ] **Step 1: tests/test_balances.py (failing)** — includes the real rent case and the Σ=0 invariant.

```python
from decimal import Decimal

from app.balances import compute_balances, suggest_transfers

D = Decimal


def test_rent_case():
    # Lyuda & Mikita each paid 2600; split Sam 1900 / Lyuda 1900 / Mikita 1400
    expenses = [{
        "payers": {"lyuda": D("2600"), "mikita": D("2600")},
        "shares": {"sam": D("1900"), "lyuda": D("1900"), "mikita": D("1400")},
    }]
    net = compute_balances(expenses, [])
    assert net["sam"] == D("-1900")
    assert net["lyuda"] == D("700")
    assert net["mikita"] == D("1200")
    assert sum(net.values()) == D("0")


def test_settlement_reduces_debt():
    expenses = [{"payers": {"lyuda": D("700")}, "shares": {"sam": D("700")}}]
    settlements = [{"from": "sam", "to": "lyuda", "amount": D("700")}]
    net = compute_balances(expenses, settlements)
    assert net["sam"] == D("0")
    assert net["lyuda"] == D("0")


def test_suggest_transfers_settles_to_zero():
    net = {"sam": D("-1900"), "lyuda": D("700"), "mikita": D("1200")}
    transfers = suggest_transfers(net)
    assert {(t["from"], t["to"], t["amount"]) for t in transfers} == {
        ("sam", "mikita", D("1200")),
        ("sam", "lyuda", D("700")),
    }
    # applying transfers zeroes everyone
    after = dict(net)
    for t in transfers:
        after[t["from"]] += t["amount"]
        after[t["to"]] -= t["amount"]
    assert all(v == D("0") for v in after.values())
```

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: app/balances.py**

```python
from collections import defaultdict
from decimal import Decimal

ZERO = Decimal("0.00")


def compute_balances(expenses, settlements):
    """expenses: [{"payers": {pid: Decimal}, "shares": {pid: Decimal}}]
    settlements: [{"from": pid, "to": pid, "amount": Decimal}]
    Returns {pid: net Decimal}. net>0 => group owes pid; net<0 => pid owes group.
    """
    net = defaultdict(lambda: Decimal("0"))
    for e in expenses:
        for pid, amt in e["payers"].items():
            net[pid] += amt
        for pid, amt in e["shares"].items():
            net[pid] -= amt
    for s in settlements:
        net[s["from"]] += s["amount"]
        net[s["to"]] -= s["amount"]
    return {pid: bal for pid, bal in net.items()}


def suggest_transfers(net):
    """Greedy min-transfer: largest debtor pays largest creditor."""
    debtors = sorted(([pid, -bal] for pid, bal in net.items() if bal < 0),
                     key=lambda x: x[1], reverse=True)
    creditors = sorted(([pid, bal] for pid, bal in net.items() if bal > 0),
                       key=lambda x: x[1], reverse=True)
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        d, c = debtors[i], creditors[j]
        amt = min(d[1], c[1])
        if amt > 0:
            transfers.append({"from": d[0], "to": c[0], "amount": amt})
        d[1] -= amt
        c[1] -= amt
        if d[1] == 0:
            i += 1
        if c[1] == 0:
            j += 1
    return transfers
```

- [ ] **Step 4: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: balance computation + min-transfer suggestion (validated on rent case)"
```

---

## Task 5: Errors + Auth (login, current_user, PIN reset)

**Files:** Create `app/errors.py`, `app/auth.py`, `tests/test_auth.py`

- [ ] **Step 1: app/errors.py**

```python
class ValidationError(Exception):
    pass


class VersionConflict(Exception):
    pass
```

- [ ] **Step 2: tests/test_auth.py (failing)**

```python
from app.auth import current_user, login, reset_pin, set_pin, verify_pin
from app.db import SessionLocal
from app.models import Person


def _seed(app):
    with app.app_context():
        s = SessionLocal()
        sam = Person(name="Сэм", color="#d97757", pin_hash=set_pin("1234"))
        s.add(sam)
        s.commit()
        return sam.id


def test_set_and_verify_pin(app):
    h = set_pin("1234")
    assert verify_pin(h, "1234")
    assert not verify_pin(h, "0000")


def test_login_sets_session(app):
    pid = _seed(app)
    with app.test_request_context():
        from flask import session
        assert login(pid, "1234") is True
        assert session["person_id"] == pid
        assert current_user().id == pid


def test_login_wrong_pin(app):
    pid = _seed(app)
    with app.test_request_context():
        assert login(pid, "9999") is False


def test_reset_pin(app):
    pid = _seed(app)
    with app.app_context():
        reset_pin(pid, "5678")
        s = SessionLocal()
        assert verify_pin(s.get(Person, pid).pin_hash, "5678")
```

- [ ] **Step 3: Run to verify FAIL.**

- [ ] **Step 4: app/auth.py**

```python
from functools import wraps

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import SessionLocal
from .models import Person


def set_pin(pin: str) -> str:
    return generate_password_hash(pin)


def verify_pin(pin_hash: str, pin: str) -> bool:
    return check_password_hash(pin_hash, pin)


def login(person_id: int, pin: str) -> bool:
    person = SessionLocal().get(Person, person_id)
    if person and verify_pin(person.pin_hash, pin):
        session["person_id"] = person.id
        session.permanent = True
        return True
    return False


def logout():
    session.pop("person_id", None)


def current_user():
    pid = session.get("person_id")
    return SessionLocal().get(Person, pid) if pid else None


def reset_pin(person_id: int, new_pin: str):
    person = SessionLocal().get(Person, person_id)
    person.pin_hash = set_pin(new_pin)
    SessionLocal().commit()


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("auth.login_form"))
        return view(*args, **kwargs)
    return wrapped
```

- [ ] **Step 5: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: auth — PIN hashing, login/session, current_user, reset_pin"
```

---

## Task 6: Expense service (validation + idempotency + optimistic lock)

**Files:** Create `app/expenses.py`, `tests/test_expenses.py`, `tests/test_concurrency.py`

- [ ] **Step 1: tests/test_expenses.py (failing)**

```python
from datetime import date
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.errors import ValidationError
from app.expenses import create_expense, soft_delete_expense
from app.models import Expense, ExpenseShare, Person

D = Decimal


def _people(app):
    with app.app_context():
        s = SessionLocal()
        ppl = [Person(name=n, color="#888", pin_hash="x") for n in ("Сэм", "Люда", "Микита")]
        s.add_all(ppl)
        s.commit()
        return [p.id for p in ppl]


def test_create_expense_persists_lines(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        exp = create_expense(s, created_by=sam, title="Продукты", category="Продукты",
                             spent_on=date(2026, 6, 5),
                             payers={sam: D("30.00")},
                             shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")},
                             request_id="r-1")
        assert exp.amount == D("30.00")
        assert s.query(ExpenseShare).filter_by(expense_id=exp.id).count() == 3


def test_idempotent_request_id(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        kw = dict(created_by=sam, title="X", category="Другое", spent_on=date(2026, 6, 5),
                  payers={sam: D("9.00")}, shares={sam: D("9.00")}, request_id="dup")
        a = create_expense(s, **kw)
        b = create_expense(s, **kw)
        assert a.id == b.id
        assert s.query(Expense).count() == 1


def test_rejects_shares_not_matching_total(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_expense(s, created_by=sam, title="X", category="Другое",
                           spent_on=date(2026, 6, 5),
                           payers={sam: D("30.00")},
                           shares={sam: D("10.00")}, request_id="r-2")


def test_rejects_empty_participants(app):
    sam, *_ = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_expense(s, created_by=sam, title="X", category="Другое",
                           spent_on=date(2026, 6, 5),
                           payers={sam: D("5.00")}, shares={}, request_id="r-3")


def test_soft_delete_keeps_row(app):
    sam, *_ = _people(app)
    with app.app_context():
        s = SessionLocal()
        exp = create_expense(s, created_by=sam, title="X", category="Другое",
                             spent_on=date(2026, 6, 5),
                             payers={sam: D("5.00")}, shares={sam: D("5.00")}, request_id="r-4")
        soft_delete_expense(s, exp.id, by=sam)
        assert s.get(Expense, exp.id).deleted_at is not None
```

- [ ] **Step 2: tests/test_concurrency.py (failing)** — the no-lost-data guarantee.

```python
from datetime import date
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.errors import VersionConflict
from app.expenses import create_expense, update_expense
from app.models import Person

D = Decimal


def _people(app):
    with app.app_context():
        s = SessionLocal()
        ppl = [Person(name=n, color="#888", pin_hash="x") for n in ("Сэм", "Люда", "Микита")]
        s.add_all(ppl)
        s.commit()
        return [p.id for p in ppl]


def test_optimistic_lock_blocks_stale_update(app):
    sam, lyuda, mikita = _people(app)
    with app.app_context():
        s = SessionLocal()
        exp = create_expense(s, created_by=sam, title="X", category="Другое",
                             spent_on=date(2026, 6, 5),
                             payers={sam: D("30.00")},
                             shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")},
                             request_id="c-1")
        stale_version = exp.version  # both editors loaded version 1

        # First editor wins
        update_expense(s, expense_id=exp.id, expected_version=stale_version, by=lyuda,
                       title="X edited", category="Другое", spent_on=date(2026, 6, 5),
                       payers={sam: D("30.00")},
                       shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")})

        # Second editor with the same stale version must be rejected
        with pytest.raises(VersionConflict):
            update_expense(s, expense_id=exp.id, expected_version=stale_version, by=mikita,
                           title="X clobber", category="Другое", spent_on=date(2026, 6, 5),
                           payers={sam: D("30.00")},
                           shares={sam: D("10.00"), lyuda: D("10.00"), mikita: D("10.00")})
```

- [ ] **Step 3: Run to verify FAIL.**

- [ ] **Step 4: app/expenses.py**

```python
from datetime import date, datetime
from decimal import Decimal

from .errors import ValidationError, VersionConflict
from .models import Expense, ExpensePayer, ExpenseShare


def _validate(payers: dict, shares: dict):
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
        return existing  # idempotent
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
    # Optimistic lock: only updates if version still matches.
    updated = (session.query(Expense)
               .filter_by(id=expense_id, version=expected_version, deleted_at=None)
               .update({"title": title, "category": category, "amount": total,
                        "spent_on": spent_on, "note": note,
                        "version": expected_version + 1}))
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
    return session.get(Expense, expense_id)


def soft_delete_expense(session, expense_id, *, by):
    exp = session.get(Expense, expense_id)
    if exp and exp.deleted_at is None:
        exp.deleted_at = datetime.utcnow()
        session.commit()
    return exp
```

- [ ] **Step 5: Run + verify PASS** (`pytest tests/test_expenses.py tests/test_concurrency.py -v`).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: expense service — validation, idempotency, optimistic-lock updates, soft delete"
```

---

## Task 7: Settlement service

**Files:** Create `app/settlements.py`, `tests/test_settlements.py`

- [ ] **Step 1: tests/test_settlements.py (failing)**

```python
from datetime import date
from decimal import Decimal

import pytest

from app.db import SessionLocal
from app.errors import ValidationError
from app.models import Person
from app.settlements import create_settlement

D = Decimal


def _people(app):
    with app.app_context():
        s = SessionLocal()
        ppl = [Person(name=n, color="#888", pin_hash="x") for n in ("Сэм", "Люда")]
        s.add_all(ppl)
        s.commit()
        return [p.id for p in ppl]


def test_create_settlement(app):
    sam, lyuda = _people(app)
    with app.app_context():
        s = SessionLocal()
        st = create_settlement(s, from_person=sam, to_person=lyuda, amount=D("700.00"),
                               method="cash", settled_on=date(2026, 6, 5),
                               created_by=sam, request_id="s-1")
        assert st.amount == D("700.00")


def test_reject_self_settlement(app):
    sam, lyuda = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_settlement(s, from_person=sam, to_person=sam, amount=D("10.00"),
                              method="cash", settled_on=date(2026, 6, 5),
                              created_by=sam, request_id="s-2")


def test_reject_non_positive(app):
    sam, lyuda = _people(app)
    with app.app_context():
        s = SessionLocal()
        with pytest.raises(ValidationError):
            create_settlement(s, from_person=sam, to_person=lyuda, amount=D("0.00"),
                              method="cash", settled_on=date(2026, 6, 5),
                              created_by=sam, request_id="s-3")
```

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: app/settlements.py**

```python
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
        st.deleted_at = datetime.utcnow()
        session.commit()
    return st
```

- [ ] **Step 4: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: settlement service (validation, idempotency, soft delete)"
```

---

## Task 8: Comments + feed assembly

**Files:** Create `app/comments.py`, `app/feed.py`, add tests to `tests/test_views.py` later (feed exercised in views). Unit test feed assembly here.

- [ ] **Step 1: app/comments.py**

```python
from datetime import datetime

from .errors import ValidationError
from .models import Comment


def add_comment(session, *, target_type, target_id, author_id, text):
    text = (text or "").strip()
    if not text:
        raise ValidationError("Пустой комментарий")
    if target_type not in ("expense", "settlement"):
        raise ValidationError("Неверный тип цели")
    c = Comment(target_type=target_type, target_id=target_id, author_id=author_id, text=text)
    session.add(c)
    session.commit()
    return c


def comments_for(session, target_type, target_id):
    return (session.query(Comment)
            .filter_by(target_type=target_type, target_id=target_id, deleted_at=None)
            .order_by(Comment.created_at.asc()).all())


def soft_delete_comment(session, comment_id, *, by):
    c = session.get(Comment, comment_id)
    if c and c.deleted_at is None:
        c.deleted_at = datetime.utcnow()
        session.commit()
    return c
```

- [ ] **Step 2: app/feed.py**

```python
from .comments import comments_for
from .models import Comment, Expense, Settlement


def _people_map(session):
    from .models import Person
    return {p.id: p for p in session.query(Person).all()}


def build_feed(session, *, month=None, limit=100):
    """Return list of feed items (dicts) newest-first.
    Each item: {kind, id, when, actor, summary, comment_count}."""
    items = []
    eq = session.query(Expense).filter_by(deleted_at=None)
    sq = session.query(Settlement).filter_by(deleted_at=None)
    if month:  # month = (year, month) filter on the activity date
        y, m = month
        eq = eq.filter(Expense.spent_on >= _first(y, m), Expense.spent_on < _next(y, m))
        sq = sq.filter(Settlement.settled_on >= _first(y, m), Settlement.settled_on < _next(y, m))
    for e in eq.all():
        items.append({"kind": "expense", "id": e.id, "when": e.created_at,
                      "actor_id": e.created_by_id, "title": e.title,
                      "amount": e.amount, "category": e.category,
                      "comment_count": _count(session, "expense", e.id)})
    for s in sq.all():
        items.append({"kind": "settlement", "id": s.id, "when": s.created_at,
                      "actor_id": s.created_by_id, "from_id": s.from_person_id,
                      "to_id": s.to_person_id, "amount": s.amount, "method": s.method,
                      "comment_count": _count(session, "settlement", s.id)})
    items.sort(key=lambda x: x["when"], reverse=True)
    return items[:limit]


def _count(session, target_type, target_id):
    return (session.query(Comment)
            .filter_by(target_type=target_type, target_id=target_id, deleted_at=None).count())


def _first(y, m):
    from datetime import date
    return date(y, m, 1)


def _next(y, m):
    from datetime import date
    return date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
```

- [ ] **Step 3: tests/test_feed.py**

```python
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
```

- [ ] **Step 4: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: comments + activity feed assembly (derived, not stored)"
```

---

## Task 9: Templates service + seed + CLI

**Files:** Create `app/templates_svc.py`, `app/cli.py`; Modify `app/__init__.py` (register CLI); Create `tests/test_templates_svc.py`

- [ ] **Step 1: tests/test_templates_svc.py (failing)**

```python
import json
from decimal import Decimal

from app.db import SessionLocal
from app.errors import ValidationError
from app.models import Expense, Person, Template
from app.templates_svc import instantiate_template

D = Decimal


def _seed_rent(app):
    with app.app_context():
        s = SessionLocal()
        names = {}
        for n, c in (("Сэм", "#d97757"), ("Люда", "#6a9bcc"), ("Микита", "#7faa6e")):
            p = Person(name=n, color=c, pin_hash="x")
            s.add(p)
            s.flush()
            names[n] = p.id
        t = Template(title="Аренда", category="Квартира (аренда)",
                     default_payers=json.dumps({"Люда": "2600", "Микита": "2600"}),
                     default_shares=json.dumps({"Сэм": "1900", "Люда": "1900", "Микита": "1400"}),
                     note="Люда→Михал Najem 1900 + Opłaty 700; Микита→Михал Najem 1900 + Opłaty 700")
        s.add(t)
        s.commit()
        return t.id, names


def test_instantiate_rent_creates_expense(app):
    tid, names = _seed_rent(app)
    with app.app_context():
        s = SessionLocal()
        exp = instantiate_template(s, template_id=tid, year=2026, month=6, by=names["Сэм"])
        assert exp.amount == D("5200")
        payers = {p.person_id: p.amount for p in exp.payers}
        assert payers[names["Люда"]] == D("2600")


def test_duplicate_month_guard(app):
    tid, names = _seed_rent(app)
    with app.app_context():
        s = SessionLocal()
        instantiate_template(s, template_id=tid, year=2026, month=6, by=names["Сэм"])
        try:
            instantiate_template(s, template_id=tid, year=2026, month=6, by=names["Сэм"])
            assert False, "expected ValidationError"
        except ValidationError:
            pass
```

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: app/templates_svc.py**

```python
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
    # duplicate-month guard
    exists = (session.query(Expense)
              .filter(Expense.template_id == template_id,
                      Expense.deleted_at.is_(None),
                      Expense.spent_on >= date(year, month, 1),
                      Expense.spent_on < (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)))
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
```

- [ ] **Step 4: app/cli.py (seed people + rent/utilities templates)**

```python
import json

import click
from flask.cli import with_appcontext

from .auth import set_pin
from .db import Base, SessionLocal, get_engine
from .models import Person, Template


@click.command("init-db")
@with_appcontext
def init_db():
    Base.metadata.create_all(get_engine())
    s = SessionLocal()
    if s.query(Person).count() == 0:
        s.add_all([
            Person(name="Сэм", color="#d97757", pin_hash=set_pin("0000")),
            Person(name="Люда", color="#6a9bcc", pin_hash=set_pin("0000")),
            Person(name="Микита", color="#7faa6e", pin_hash=set_pin("0000")),
        ])
    if s.query(Template).count() == 0:
        s.add(Template(
            title="Аренда", category="Квартира (аренда)",
            default_payers=json.dumps({"Люда": "2600", "Микита": "2600"}),
            default_shares=json.dumps({"Сэм": "1900", "Люда": "1900", "Микита": "1400"}),
            note="Люда → Михал: Najem 1900, Opłaty 700\nМикита → Михал: Najem 1900, Opłaty 700",
        ))
    s.commit()
    click.echo("DB initialised. Default PIN for everyone: 0000 (change it).")
```

- [ ] **Step 5: Register CLI in app/__init__.py** — add inside `create_app`, before `return app`:

```python
    from .cli import init_db
    app.cli.add_command(init_db)
```

- [ ] **Step 6: Run + verify PASS** (`pytest tests/test_templates_svc.py -v`). Commit:

```bash
git add -A && git commit -m "feat: rent template instantiation + duplicate-month guard + init-db seed"
```

---

## Task 10: Base layout + Claude-style CSS + nav

**Files:** Create `app/templates/base.html`, `app/static/styles.css`, `app/static/app.js`

- [ ] **Step 1: app/templates/base.html**

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#262624">
  <link rel="manifest" href="{{ url_for('static', filename='manifest.webmanifest') }}">
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
  <title>Котёл</title>
  <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
  <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
  <script src="{{ url_for('static', filename='app.js') }}" defer></script>
</head>
<body>
  <main class="shell">
    {% block content %}{% endblock %}
  </main>
  {% if current_user %}
  <nav class="tabbar">
    <a href="{{ url_for('balance.index') }}" class="{{ 'active' if active=='balance' }}">Баланс</a>
    <a href="{{ url_for('feed.index') }}" class="{{ 'active' if active=='feed' }}">Лента</a>
    <a href="{{ url_for('expense.new') }}" class="add">＋</a>
    <a href="{{ url_for('profile.index') }}" class="{{ 'active' if active=='profile' }}">Профиль</a>
  </nav>
  {% endif %}
  {% if current_user %}<script>window.KOTEL_USER = "{{ current_user.name }}";</script>{% endif %}
</body>
</html>
```

- [ ] **Step 2: app/static/styles.css** (Claude palette: warm dark, narrow column, cards)

```css
:root {
  --bg: #262624; --surface: #30302e; --surface-2: #3a3a37;
  --text: #f5f4ef; --muted: #b4b2a8; --line: #45443f;
  --accent: #d97757; --ok: #7faa6e; --warn: #d9a14f;
  --radius: 14px; --maxw: 540px;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.shell { max-width: var(--maxw); margin: 0 auto; padding: 20px 16px 96px; }
h1 { font-size: 20px; font-weight: 600; margin: 4px 0 16px; }
.card { background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 16px; margin-bottom: 12px; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.muted { color: var(--muted); }
.amount { font-variant-numeric: tabular-nums; font-weight: 600; }
.pill { display: inline-block; padding: 2px 10px; border-radius: 999px;
  background: var(--surface-2); color: var(--muted); font-size: 13px; }
button, .btn { font: inherit; border: 0; border-radius: 10px; padding: 12px 16px;
  background: var(--accent); color: #1a1a18; font-weight: 600; cursor: pointer; width: 100%; }
.btn-ghost { background: var(--surface-2); color: var(--text); }
input, select, textarea { width: 100%; font: inherit; color: var(--text);
  background: var(--surface-2); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px; margin-top: 6px; }
label { display: block; margin-top: 12px; font-size: 14px; color: var(--muted); }
.tabbar { position: fixed; bottom: 0; left: 0; right: 0; display: flex;
  max-width: var(--maxw); margin: 0 auto; background: var(--surface);
  border-top: 1px solid var(--line); }
.tabbar a { flex: 1; text-align: center; padding: 14px 0; color: var(--muted);
  text-decoration: none; font-size: 14px; }
.tabbar a.active { color: var(--text); }
.tabbar a.add { color: var(--accent); font-size: 22px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.chip { padding: 8px 12px; border-radius: 999px; background: var(--surface-2);
  border: 1px solid var(--line); color: var(--muted); cursor: pointer; font-size: 14px; }
.chip[aria-pressed="true"] { background: var(--accent); color: #1a1a18; border-color: var(--accent); }
.collapse { margin-top: 10px; }
.warn { color: var(--warn); font-size: 14px; margin-top: 8px; }
details > summary { cursor: pointer; color: var(--muted); list-style: none; }
```

- [ ] **Step 3: app/static/app.js** (idempotency key + tiny helpers)

```javascript
// Generate a per-form idempotency key so double-submits / retries don't duplicate.
document.addEventListener("htmx:configRequest", (e) => {
  const form = e.detail.elt.closest("form");
  if (form && form.dataset.idempotent && !form.dataset.reqid) {
    form.dataset.reqid = (crypto.randomUUID && crypto.randomUUID()) ||
      String(Date.now()) + Math.random().toString(16).slice(2);
  }
  if (form && form.dataset.reqid) e.detail.parameters["request_id"] = form.dataset.reqid;
});

// PWA service worker.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () =>
    navigator.serviceWorker.register("/static/sw.js").catch(() => {}));
}
```

- [ ] **Step 4: Manual check** — defer rendering until views exist (Task 11). Commit:

```bash
git add -A && git commit -m "feat: base layout, Claude-style CSS, idempotency-key JS"
```

---

## Task 11: Auth views + login screen

**Files:** Create `app/views/__init__.py`, `app/views/auth_views.py`, `app/templates/login.html`; Modify `app/__init__.py` (register blueprint + inject current_user)

- [ ] **Step 1: app/views/auth_views.py**

```python
from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import login, logout
from ..db import SessionLocal
from ..models import Person

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login_form():
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("login.html", people=people)


@bp.post("/login")
def do_login():
    pid = int(request.form["person_id"])
    if login(pid, request.form.get("pin", "")):
        return redirect(url_for("balance.index"))
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("login.html", people=people, error="Неверный PIN"), 401


@bp.post("/logout")
def do_logout():
    logout()
    return redirect(url_for("auth.login_form"))
```

- [ ] **Step 2: app/templates/login.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>Котёл</h1>
<form method="post" action="{{ url_for('auth.do_login') }}"
      x-data="{ pid: null }">
  <p class="muted">Кто ты?</p>
  <div class="chips">
    {% for p in people %}
    <button type="button" class="chip" :aria-pressed="pid==={{ p.id }}"
            @click="pid={{ p.id }}" style="border-color: {{ p.color }}">{{ p.name }}</button>
    {% endfor %}
  </div>
  <input type="hidden" name="person_id" :value="pid">
  <label>PIN<input name="pin" inputmode="numeric" autocomplete="off" maxlength="8"></label>
  {% if error %}<p class="warn">{{ error }}</p>{% endif %}
  <button class="btn" style="margin-top:16px" :disabled="pid===null">Войти</button>
</form>
{% endblock %}
```

- [ ] **Step 3: Modify app/__init__.py** — register blueprint + inject `current_user` into templates. Add before `return app`:

```python
    from .auth import current_user as _current_user
    from .views.auth_views import bp as auth_bp
    app.register_blueprint(auth_bp)

    @app.context_processor
    def _inject_user():
        return {"current_user": _current_user()}
```

- [ ] **Step 4: tests/test_views.py — add login flow test**

```python
def test_login_redirects(client, app):
    from app.auth import set_pin
    from app.db import SessionLocal
    from app.models import Person
    with app.app_context():
        s = SessionLocal()
        s.add(Person(name="Сэм", color="#d97757", pin_hash=set_pin("1234")))
        s.commit()
        pid = s.query(Person).first().id
    resp = client.post("/login", data={"person_id": pid, "pin": "1234"})
    assert resp.status_code == 302
```

- [ ] **Step 5: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: auth views + login screen (pick person + PIN)"
```

---

## Task 12: Expense views + form (simple + advanced split) + HTMX

**Files:** Create `app/views/expense_views.py`, `app/templates/expense_form.html`; Modify `app/__init__.py` (register)

- [ ] **Step 1: app/views/expense_views.py**

```python
from datetime import date
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..db import SessionLocal
from ..errors import ValidationError
from ..expenses import create_expense
from ..models import Person, Template
from ..money import parse_amount, split_equal

bp = Blueprint("expense", __name__)

CATEGORIES = ["Квартира (аренда)", "Коммуналка", "Продукты", "Хозтовары", "Кафе/досуг", "Другое"]


@bp.get("/expense/new")
@require_login
def new():
    s = SessionLocal()
    people = s.query(Person).order_by(Person.id).all()
    templates = s.query(Template).filter_by(active=True).all()
    return render_template("expense_form.html", people=people, templates=templates,
                           categories=CATEGORIES, today=date.today().isoformat(), active="add")


@bp.post("/expense")
@require_login
def create():
    s = SessionLocal()
    me = current_user()
    form = request.form
    try:
        amount = parse_amount(form["amount"])
        payer_id = int(form.get("payer_id", me.id))
        participants = [int(x) for x in form.getlist("participant")]
        if not participants:
            raise ValidationError("Выбери хотя бы одного участника")
        amounts = split_equal(amount, len(participants))
        shares = {pid: amt for pid, amt in zip(participants, amounts)}
        exp = create_expense(s, created_by=me.id, title=form["title"].strip() or "Без названия",
                             category=form.get("category", "Другое"),
                             spent_on=date.fromisoformat(form.get("spent_on", date.today().isoformat())),
                             payers={payer_id: amount}, shares=shares,
                             request_id=form["request_id"])
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return redirect(url_for("feed.index"))
```

- [ ] **Step 2: app/templates/expense_form.html** (simple by default, advanced collapsed)

```html
{% extends "base.html" %}
{% block content %}
<h1>Новая трата</h1>

<div class="chips" style="margin-bottom:12px">
  {% for t in templates %}
  <form method="post" action="{{ url_for('expense.from_template', template_id=t.id) }}">
    <button class="chip" type="submit">＋ {{ t.title }} (этот месяц)</button>
  </form>
  {% endfor %}
</div>

<form method="post" action="{{ url_for('expense.create') }}" data-idempotent="1"
      hx-post="{{ url_for('expense.create') }}" hx-target="#form-error"
      x-data="{ payer: {{ current_user.id }},
                participants: [{% for p in people %}{{ p.id }}{{ ',' if not loop.last }}{% endfor %}] }">
  <label>Сумма, zł<input name="amount" inputmode="decimal" required></label>
  <label>Название<input name="title" placeholder="Продукты"></label>

  <label>Категория</label>
  <div class="chips" x-data="{ cat: 'Другое' }">
    {% for c in categories %}
    <button type="button" class="chip" :aria-pressed="cat==='{{ c }}'" @click="cat='{{ c }}'">{{ c }}</button>
    {% endfor %}
    <input type="hidden" name="category" :value="cat">
  </div>

  <details class="collapse">
    <summary>Разделить иначе · кто платил</summary>
    <label>Платил</label>
    <div class="chips">
      {% for p in people %}
      <button type="button" class="chip" :aria-pressed="payer==={{ p.id }}" @click="payer={{ p.id }}">{{ p.name }}</button>
      {% endfor %}
      <input type="hidden" name="payer_id" :value="payer">
    </div>
    <label>Делим на</label>
    <div class="chips">
      {% for p in people %}
      <button type="button" class="chip"
              :aria-pressed="participants.includes({{ p.id }})"
              @click="participants.includes({{ p.id }})
                        ? participants = participants.filter(x => x !== {{ p.id }})
                        : participants.push({{ p.id }})">{{ p.name }}</button>
      {% endfor %}
    </div>
  </details>

  <template x-for="pid in participants" :key="pid">
    <input type="hidden" name="participant" :value="pid">
  </template>
  <input type="hidden" name="spent_on" value="{{ today }}">

  <div id="form-error"></div>
  <button class="btn" style="margin-top:16px">Добавить</button>
</form>
{% endblock %}
```

- [ ] **Step 3: app/templates/partials/form_error.html**

```html
<p class="warn">{{ error }}</p>
```

- [ ] **Step 4: Add template instantiation route** to `app/views/expense_views.py`:

```python
from ..templates_svc import instantiate_template


@bp.post("/expense/from-template/<int:template_id>")
@require_login
def from_template(template_id):
    s = SessionLocal()
    today = date.today()
    try:
        instantiate_template(s, template_id=template_id, year=today.year, month=today.month,
                             by=current_user().id)
    except ValidationError as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return redirect(url_for("feed.index"))
```

- [ ] **Step 5: Register blueprint** in `app/__init__.py`:

```python
    from .views.expense_views import bp as expense_bp
    app.register_blueprint(expense_bp)
```

- [ ] **Step 6: tests/test_views.py — add expense creation test** (logged-in session)

```python
def _login(client, app, name="Сэм"):
    from app.auth import set_pin
    from app.db import SessionLocal
    from app.models import Person
    with app.app_context():
        s = SessionLocal()
        if not s.query(Person).filter_by(name=name).first():
            s.add_all([Person(name=n, color="#888", pin_hash=set_pin("1234"))
                       for n in ("Сэм", "Люда", "Микита")])
            s.commit()
        pid = s.query(Person).filter_by(name=name).first().id
    client.post("/login", data={"person_id": pid, "pin": "1234"})
    return pid


def test_create_expense_via_form(client, app):
    _login(client, app)
    from app.db import SessionLocal
    from app.models import Person
    with app.app_context():
        ids = [p.id for p in SessionLocal().query(Person).order_by(Person.id).all()]
    resp = client.post("/expense", data={
        "amount": "30", "title": "Продукты", "category": "Продукты",
        "payer_id": ids[0], "participant": ids, "spent_on": "2026-06-05",
        "request_id": "form-1"})
    assert resp.status_code in (302, 200)
    from app.expenses import create_expense  # noqa
    from app.models import Expense
    with app.app_context():
        assert SessionLocal().query(Expense).filter_by(request_id="form-1").count() == 1
```

- [ ] **Step 7: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: expense form (simple + advanced split) + template buttons + HTMX"
```

---

## Task 13: Balance view + graph + settle form

**Files:** Create `app/views/balance_views.py`, `app/views/settlement_views.py`, `app/templates/balance.html`, `app/templates/settle_form.html`, `app/templates/partials/graph.html`; Modify `app/__init__.py`

- [ ] **Step 1: app/views/balance_views.py**

```python
from flask import Blueprint, render_template

from ..auth import require_login
from ..balances import compute_balances, suggest_transfers
from ..db import SessionLocal
from ..models import Expense, ExpensePayer, ExpenseShare, Person, Settlement

bp = Blueprint("balance", __name__)


def _load_balances(s):
    people = {p.id: p for p in s.query(Person).all()}
    expenses = []
    for e in s.query(Expense).filter_by(deleted_at=None).all():
        payers = {p.person_id: p.amount for p in s.query(ExpensePayer).filter_by(expense_id=e.id)}
        shares = {p.person_id: p.amount for p in s.query(ExpenseShare).filter_by(expense_id=e.id)}
        expenses.append({"payers": payers, "shares": shares})
    settlements = [{"from": x.from_person_id, "to": x.to_person_id, "amount": x.amount}
                   for x in s.query(Settlement).filter_by(deleted_at=None).all()]
    net = compute_balances(expenses, settlements)
    transfers = suggest_transfers(net)
    return people, net, transfers


@bp.get("/")
@require_login
def index():
    s = SessionLocal()
    people, net, transfers = _load_balances(s)
    invariant_ok = sum(net.values(), __import__("decimal").Decimal("0")) == 0
    return render_template("balance.html", people=people, net=net, transfers=transfers,
                           invariant_ok=invariant_ok, active="balance")
```

- [ ] **Step 2: app/templates/balance.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="row"><h1>Баланс</h1>
  <form method="post" action="{{ url_for('auth.do_logout') }}"><button class="chip">{{ current_user.name }} ⎋</button></form>
</div>

{% if not invariant_ok %}<p class="warn">⚠ Баланс не сходится к нулю — сообщи разработчику.</p>{% endif %}

{% set mine = net.get(current_user.id, 0) %}
<div class="card">
  {% set owe = transfers | selectattr('from', 'equalto', current_user.id) | list %}
  {% set owed = transfers | selectattr('to', 'equalto', current_user.id) | list %}
  <p class="muted">Ты должен</p>
  {% if owe %}{% for t in owe %}
    <div class="row"><span>{{ people[t.to].name }}</span><span class="amount">{{ '%.2f' % t.amount }} zł</span></div>
  {% endfor %}{% else %}<p>—</p>{% endif %}
  <p class="muted" style="margin-top:12px">Тебе должны</p>
  {% if owed %}{% for t in owed %}
    <div class="row"><span>{{ people[t.from].name }}</span><span class="amount">{{ '%.2f' % t.amount }} zł</span></div>
  {% endfor %}{% else %}<p>—</p>{% endif %}
</div>

<details class="card">
  <summary>△ Показать граф</summary>
  {% include "partials/graph.html" %}
</details>

<div class="card">
  <p class="muted">Чтобы всё закрыть</p>
  {% for t in transfers %}
  <div class="row"><span>{{ people[t.from].name }} → {{ people[t.to].name }}</span>
    <span class="amount">{{ '%.2f' % t.amount }} zł</span></div>
  {% endfor %}
  {% if not transfers %}<p>Все в расчёте 🎉</p>{% endif %}
</div>

<a class="btn" href="{{ url_for('settlement.new') }}">Закрыть долг</a>
{% endblock %}
```

- [ ] **Step 3: app/templates/partials/graph.html** (simple SVG triangle of debts)

```html
<svg viewBox="0 0 240 200" width="100%" style="max-width:280px;display:block;margin:10px auto">
  {% set pos = {} %}
  {% for pid, p in people.items() %}{% set _ = pos.update({pid: loop.index0}) %}{% endfor %}
  {% set coords = [[120,30],[30,170],[210,170]] %}
  {% for t in transfers %}
    {% set a = coords[pos[t.from]] %}{% set b = coords[pos[t.to]] %}
    <line x1="{{ a[0] }}" y1="{{ a[1] }}" x2="{{ b[0] }}" y2="{{ b[1] }}"
          stroke="#d97757" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="{{ (a[0]+b[0])//2 }}" y="{{ (a[1]+b[1])//2 }}" fill="#b4b2a8" font-size="11">{{ '%.0f'|format(t.amount) }}</text>
  {% endfor %}
  {% for pid, p in people.items() %}
    <circle cx="{{ coords[pos[pid]][0] }}" cy="{{ coords[pos[pid]][1] }}" r="22" fill="{{ p.color }}"/>
    <text x="{{ coords[pos[pid]][0] }}" y="{{ coords[pos[pid]][1]+4 }}" text-anchor="middle" font-size="10" fill="#1a1a18">{{ p.name }}</text>
  {% endfor %}
  <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <path d="M0,0 L6,3 L0,6 Z" fill="#d97757"/></marker></defs>
</svg>
```

- [ ] **Step 4: app/views/settlement_views.py**

```python
from datetime import date
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..db import SessionLocal
from ..errors import ValidationError
from ..money import parse_amount
from ..models import Person
from ..settlements import create_settlement

bp = Blueprint("settlement", __name__)


@bp.get("/settle")
@require_login
def new():
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("settle_form.html", people=people, active="balance",
                           today=date.today().isoformat())


@bp.post("/settle")
@require_login
def create():
    me = current_user()
    s = SessionLocal()
    form = request.form
    try:
        create_settlement(s, from_person=me.id, to_person=int(form["to_person"]),
                          amount=parse_amount(form["amount"]), method=form.get("method", "cash"),
                          settled_on=date.fromisoformat(form.get("settled_on")),
                          created_by=me.id, request_id=form["request_id"])
    except (ValidationError, ValueError) as e:
        return render_template("partials/form_error.html", error=str(e)), 422
    return redirect(url_for("balance.index"))
```

- [ ] **Step 5: app/templates/settle_form.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>Закрыть долг</h1>
<form method="post" action="{{ url_for('settlement.create') }}" data-idempotent="1"
      x-data="{ to: null, method: 'cash' }">
  <label>Кому</label>
  <div class="chips">
    {% for p in people if p.id != current_user.id %}
    <button type="button" class="chip" :aria-pressed="to==={{ p.id }}" @click="to={{ p.id }}">{{ p.name }}</button>
    {% endfor %}
    <input type="hidden" name="to_person" :value="to">
  </div>
  <label>Сумма, zł<input name="amount" inputmode="decimal" required></label>
  <label>Как</label>
  <div class="chips">
    <button type="button" class="chip" :aria-pressed="method==='cash'" @click="method='cash'">Наличкой</button>
    <button type="button" class="chip" :aria-pressed="method==='transfer'" @click="method='transfer'">Переводом</button>
    <input type="hidden" name="method" :value="method">
  </div>
  <input type="hidden" name="settled_on" value="{{ today }}">
  <div id="form-error"></div>
  <button class="btn" style="margin-top:16px" :disabled="to===null">Готово</button>
</form>
{% endblock %}
```

- [ ] **Step 6: Register blueprints** in `app/__init__.py`:

```python
    from .views.balance_views import bp as balance_bp
    from .views.settlement_views import bp as settlement_bp
    app.register_blueprint(balance_bp)
    app.register_blueprint(settlement_bp)
```

- [ ] **Step 7: tests/test_views.py — balance + settle**

```python
def test_balance_and_settlement_zeroes(client, app):
    _login(client, app)
    from app.db import SessionLocal
    from app.models import Person
    with app.app_context():
        ids = {p.name: p.id for p in SessionLocal().query(Person).all()}
    # Lyuda pays 700 for Sam
    client.post("/expense", data={"amount": "700", "title": "X", "category": "Другое",
        "payer_id": ids["Люда"], "participant": [ids["Сэм"]], "spent_on": "2026-06-05",
        "request_id": "b-1"})
    r = client.get("/")
    assert r.status_code == 200
    # Sam settles 700 to Lyuda
    client.post("/settle", data={"to_person": ids["Люда"], "amount": "700",
        "method": "cash", "settled_on": "2026-06-05", "request_id": "set-1"})
    assert client.get("/").status_code == 200
```

- [ ] **Step 8: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: balance screen + debt graph + settle flow"
```

---

## Task 14: Feed view + comments UI

**Files:** Create `app/views/feed_views.py`, `app/templates/feed.html`, `app/templates/partials/comments.html`; Modify `app/__init__.py`

- [ ] **Step 1: app/views/feed_views.py**

```python
from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login
from ..comments import add_comment, comments_for
from ..db import SessionLocal
from ..errors import ValidationError
from ..feed import build_feed
from ..models import Person

bp = Blueprint("feed", __name__)


@bp.get("/feed")
@require_login
def index():
    s = SessionLocal()
    people = {p.id: p for p in s.query(Person).all()}
    return render_template("feed.html", items=build_feed(s), people=people, active="feed")


@bp.get("/item/<target_type>/<int:target_id>/comments")
@require_login
def comments(target_type, target_id):
    s = SessionLocal()
    people = {p.id: p for p in s.query(Person).all()}
    return render_template("partials/comments.html", target_type=target_type,
                           target_id=target_id, comments=comments_for(s, target_type, target_id),
                           people=people)


@bp.post("/item/<target_type>/<int:target_id>/comments")
@require_login
def post_comment(target_type, target_id):
    s = SessionLocal()
    try:
        add_comment(s, target_type=target_type, target_id=target_id,
                    author_id=current_user().id, text=request.form.get("text", ""))
    except ValidationError:
        pass
    return redirect(url_for("feed.comments", target_type=target_type, target_id=target_id))
```

- [ ] **Step 2: app/templates/feed.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>Лента</h1>
{% for it in items %}
<div class="card">
  <div class="row">
    <span>
      <strong>{{ people[it.actor_id].name }}</strong>
      {% if it.kind == 'expense' %}· {{ it.title }}
      {% else %}→ {{ people[it.to_id].name }}{% endif %}
    </span>
    <span class="amount">{{ '%.2f' % it.amount }} zł</span>
  </div>
  <div class="row">
    <span class="pill">{% if it.kind=='expense' %}{{ it.category }}{% else %}{{ 'нал' if it.method=='cash' else 'перевод' }}{% endif %}</span>
    <button type="button" class="chip" style="width:auto"
            hx-get="{{ url_for('feed.comments', target_type=it.kind, target_id=it.id) }}"
            hx-target="#c-{{ it.kind }}-{{ it.id }}" hx-swap="innerHTML">💬 {{ it.comment_count }}</button>
  </div>
  <div id="c-{{ it.kind }}-{{ it.id }}" class="collapse"></div>
</div>
{% else %}
<p class="muted">Пока пусто. Добавь первую трату через ＋.</p>
{% endfor %}
{% endblock %}
```

- [ ] **Step 3: app/templates/partials/comments.html**

```html
{% for c in comments %}
<div class="row" style="margin-top:6px">
  <span><strong>{{ people[c.author_id].name }}:</strong> {{ c.text }}</span>
</div>
{% endfor %}
<form method="post" action="{{ url_for('feed.post_comment', target_type=target_type, target_id=target_id) }}"
      hx-post="{{ url_for('feed.post_comment', target_type=target_type, target_id=target_id) }}"
      hx-target="#c-{{ target_type }}-{{ target_id }}" hx-swap="innerHTML" style="margin-top:8px">
  <input name="text" placeholder="Комментарий…" autocomplete="off">
</form>
```

- [ ] **Step 4: Register blueprint** in `app/__init__.py`:

```python
    from .views.feed_views import bp as feed_bp
    app.register_blueprint(feed_bp)
```

- [ ] **Step 5: tests/test_views.py — feed loads**

```python
def test_feed_loads(client, app):
    _login(client, app)
    assert client.get("/feed").status_code == 200
```

- [ ] **Step 6: Run + verify PASS.** Commit:

```bash
git add -A && git commit -m "feat: activity feed + inline comments (collapsed, HTMX)"
```

---

## Task 15: Profile view (PIN change + reset for others)

**Files:** Create `app/views/profile_views.py`, `app/templates/profile.html`; Modify `app/__init__.py`

- [ ] **Step 1: app/views/profile_views.py**

```python
from flask import Blueprint, redirect, render_template, request, url_for

from ..auth import current_user, require_login, reset_pin
from ..db import SessionLocal
from ..models import Person

bp = Blueprint("profile", __name__)


@bp.get("/profile")
@require_login
def index():
    people = SessionLocal().query(Person).order_by(Person.id).all()
    return render_template("profile.html", people=people, active="profile")


@bp.post("/profile/pin")
@require_login
def change_pin():
    reset_pin(current_user().id, request.form["pin"])
    return redirect(url_for("profile.index"))


@bp.post("/profile/reset/<int:person_id>")
@require_login
def reset_other(person_id):
    reset_pin(person_id, request.form.get("pin", "0000"))
    return redirect(url_for("profile.index"))
```

- [ ] **Step 2: app/templates/profile.html**

```html
{% extends "base.html" %}
{% block content %}
<h1>Профиль — {{ current_user.name }}</h1>
<form method="post" action="{{ url_for('profile.change_pin') }}" class="card">
  <label>Сменить свой PIN<input name="pin" inputmode="numeric" maxlength="8" required></label>
  <button class="btn" style="margin-top:12px">Сохранить</button>
</form>
<div class="card">
  <p class="muted">Соседи (можно сбросить PIN, если кто-то забыл)</p>
  {% for p in people if p.id != current_user.id %}
  <form method="post" action="{{ url_for('profile.reset_other', person_id=p.id) }}"
        class="row" style="margin-top:8px">
    <span>{{ p.name }}</span>
    <span style="display:flex;gap:6px"><input name="pin" placeholder="новый PIN" style="width:120px">
    <button class="chip" style="width:auto">Сбросить</button></span>
  </form>
  {% endfor %}
</div>
<form method="post" action="{{ url_for('auth.do_logout') }}"><button class="btn-ghost btn">Выйти</button></form>
{% endblock %}
```

- [ ] **Step 3: Register blueprint** in `app/__init__.py`:

```python
    from .views.profile_views import bp as profile_bp
    app.register_blueprint(profile_bp)
```

- [ ] **Step 4: Run app smoke test + verify PASS** (`pytest -q`). Commit:

```bash
git add -A && git commit -m "feat: profile screen — change own PIN, reset neighbour's PIN, logout"
```

---

## Task 16: PWA (manifest + service worker) + README + CLAUDE.md

**Files:** Create `app/static/manifest.webmanifest`, `app/static/sw.js`, `README.md`, `CLAUDE.md`

- [ ] **Step 1: app/static/manifest.webmanifest**

```json
{
  "name": "Котёл",
  "short_name": "Котёл",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#262624",
  "theme_color": "#262624",
  "icons": [
    { "src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 2: app/static/sw.js** (cache app shell; network-first for navigations)

```javascript
const CACHE = "kotel-v1";
const SHELL = ["/static/styles.css", "/static/app.js", "/static/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return; // never cache writes
  if (SHELL.includes(url.pathname)) {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
});
```

Note: generate two placeholder PNG icons (192/512) or drop them — a missing icon only warns, doesn't break install. Add real icons later.

- [ ] **Step 3: README.md**

```markdown
# Котёл

Сплиттер расходов на квартиру для троих (zł). Flask + HTMX + SQLite, PWA.

## Запуск
    python -m venv .venv && . .venv/Scripts/activate   # Windows
    pip install -r requirements.txt
    set SECRET_KEY=change-me                            # or export on *nix
    flask --app wsgi init-db                            # creates tables, seeds people (PIN 0000) + rent template
    flask --app wsgi run --port 8000
    # open http://localhost:8000 — log in, change PINs in Профиль

## Тесты
    pytest -q
```

- [ ] **Step 4: CLAUDE.md** (source of truth)

```markdown
# Котёл — сплиттер расходов на квартиру (3 соседа, zł)

Flask + HTMX + Alpine + SQLite (WAL). PWA. Не SPA. Источник истины — этот файл и
docs/superpowers/specs/2026-06-05-kotel-design.md.

## Принципы
- Балансы НЕ хранятся — считаются на чтении из неизменяемых записей (нет гонки на счётчике).
- Правки траты — через оптимистичную блокировку (version). Записи — idempotency_key.
- Удаление — мягкое (deleted_at). Деньги/комментарии не теряются.
- Чистая логика (money.py, balances.py) — без Flask/DB, покрыта тестами.
- Сервисы владеют записью+валидацией; views тонкие.
- Одна валюта (zł), одна квартира, без уведомлений. UI без перегруза: прогрессивное раскрытие.

## Структура
app/ — models, money, balances, auth, expenses, settlements, comments, feed, templates_svc, views/
tests/ — pytest

## Запуск
flask --app wsgi init-db && flask --app wsgi run --port 8000
```

- [ ] **Step 5: Final full test run** — `pytest -q` (all green). Manual: `flask --app wsgi init-db && flask --app wsgi run`, open in browser, log in, add expense, settle, comment.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: PWA manifest + service worker, README, CLAUDE.md"
```

---

## Self-Review (done by plan author)

**Spec coverage:**
- Profile+PIN identity → Tasks 5, 11, 15 ✓
- Single currency zł → no currency fields anywhere ✓
- Payers/shares expense model → Tasks 3, 6 ✓
- Rent case (5200, two payers, exclusion) → Tasks 4, 9 ✓
- Derived balances + Σ=0 invariant + min-transfer → Tasks 4, 13 ✓
- Settlements ("closed a debt") → Tasks 7, 13 ✓
- Comments (collapsed) → Tasks 8, 14 ✓
- Activity feed (derived) → Tasks 8, 14 ✓
- Templates + duplicate-month guard → Task 9 ✓
- Categories (fixed chips) → Task 12 ✓
- Concurrency/no-lost-data: immutable+derived (Task 4), optimistic lock (Task 6), idempotency (Tasks 6/7 + app.js Task 10), soft-delete (Tasks 6/7/8), WAL (Task 1) ✓
- Mobile-first Claude UI, progressive disclosure → Tasks 10–15 ✓
- PWA → Task 16 ✓

**Open items intentionally deferred:** app icons (placeholder), deploy target (local `flask run` documented; Docker can be added later), background feed auto-refresh polling (can add `hx-trigger="every 10s"` to feed later — not required for correctness).

**Type consistency:** service signatures (`create_expense`, `update_expense`, `create_settlement`, `instantiate_template`, `build_feed`, `compute_balances`, `suggest_transfers`) are used with identical names/args across tasks ✓.
