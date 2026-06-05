PINS = {"Сэм": "111", "Люда": "222", "Микита": "333"}


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def _seed_people(app):
    from app.auth import set_pin
    from app.db import SessionLocal
    from app.models import Person
    with app.app_context():
        s = SessionLocal()
        if s.query(Person).count() == 0:
            s.add_all([Person(name=n, color="#888", pin_hash=set_pin(PINS[n]))
                       for n in ("Сэм", "Люда", "Микита")])
            s.commit()
        return {p.name: p.id for p in s.query(Person).order_by(Person.id).all()}


def _login(client, app, name="Сэм"):
    ids = _seed_people(app)
    client.post("/login", data={"pin": PINS[name]})
    return ids


def test_login_page_renders(client, app):
    assert client.get("/login").status_code == 200


def test_login_by_pin_redirects(client, app):
    _seed_people(app)
    assert client.post("/login", data={"pin": "111"}).status_code == 302


def test_login_wrong_pin(client, app):
    _seed_people(app)
    assert client.post("/login", data={"pin": "000"}).status_code == 401


def test_requires_login(client, app):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_home_and_settle_render(client, app):
    _login(client, app)
    assert client.get("/").status_code == 200
    assert client.get("/settle").status_code == 200
    assert client.get("/partials/home").status_code == 200


def test_create_expense_payer_is_current_user(client, app):
    ids = _login(client, app)  # Сэм
    client.post("/expense", data={"amount": "30", "title": "Продукты", "category": "Продукты",
        "participant": [ids["Сэм"], ids["Люда"], ids["Микита"]], "spent_on": "2026-06-05",
        "note": "помидоры", "request_id": "f-1"})
    from app.db import SessionLocal
    from app.models import Expense, ExpensePayer
    with app.app_context():
        s = SessionLocal()
        e = s.query(Expense).filter_by(request_id="f-1").first()
        payers = [p.person_id for p in s.query(ExpensePayer).filter_by(expense_id=e.id)]
        assert payers == [ids["Сэм"]]           # payer is always the logged-in user
        assert e.note == "помидоры"
    # note shows on home
    assert "помидоры" in client.get("/").get_data(as_text=True)


def test_balance_and_settlement(client, app):
    ids = _seed_people(app)
    # Lyuda logs in and records that SHE paid 700 for Sam
    client.post("/login", data={"pin": "222"})
    client.post("/expense", data={"amount": "700", "title": "за Сэма", "category": "Другое",
        "participant": [ids["Сэм"]], "spent_on": "2026-06-05", "request_id": "b-1"})
    client.post("/logout")
    # Sam logs in -> owes Lyuda 700, can settle
    client.post("/login", data={"pin": "111"})
    assert client.get("/").status_code == 200
    assert client.get("/settle").status_code == 200
    r = client.post("/settle", data={"to_person": ids["Люда"], "amount": "700",
        "method": "cash", "settled_on": "2026-06-05", "request_id": "set-1"})
    assert r.status_code in (302, 200)
    assert client.get("/").status_code == 200


def test_delete_own_expense(client, app):
    ids = _login(client, app)
    client.post("/expense", data={"amount": "9", "title": "oops", "category": "Другое",
        "participant": [ids["Сэм"]], "spent_on": "2026-06-05", "request_id": "d-1"})
    from app.db import SessionLocal
    from app.models import Expense
    with app.app_context():
        eid = SessionLocal().query(Expense).filter_by(request_id="d-1").first().id
    r = client.post(f"/expense/{eid}/delete")
    assert r.status_code in (302, 200)
    with app.app_context():
        assert SessionLocal().get(Expense, eid).deleted_at is not None


def test_cannot_delete_others_expense(client, app):
    ids = _seed_people(app)
    # Lyuda creates
    client.post("/login", data={"pin": "222"})
    client.post("/expense", data={"amount": "9", "title": "x", "category": "Другое",
        "participant": [ids["Люда"]], "spent_on": "2026-06-05", "request_id": "o-1"})
    client.post("/logout")
    from app.db import SessionLocal
    from app.models import Expense
    with app.app_context():
        eid = SessionLocal().query(Expense).filter_by(request_id="o-1").first().id
    # Sam tries to delete Lyuda's expense -> ignored
    client.post("/login", data={"pin": "111"})
    client.post(f"/expense/{eid}/delete")
    with app.app_context():
        assert SessionLocal().get(Expense, eid).deleted_at is None


def test_settle_screen_when_nothing_owed(client, app):
    _login(client, app)
    page = client.get("/settle")
    assert page.status_code == 200
    assert "никому не должен" in page.get_data(as_text=True)


def test_from_template_creates_rent_idempotently(client, app):
    import json
    _login(client, app)
    from app.db import SessionLocal
    from app.models import Expense, Template
    with app.app_context():
        s = SessionLocal()
        s.add(Template(title="Аренда", category="Квартира",
                       default_payers=json.dumps({"Люда": "2600", "Микита": "2600"}),
                       default_shares=json.dumps({"Сэм": "1900", "Люда": "1900", "Микита": "1400"}),
                       note="x"))
        s.commit()
        tid = s.query(Template).first().id
    assert client.post(f"/expense/from-template/{tid}").status_code in (302, 200)
    assert client.post(f"/expense/from-template/{tid}").status_code in (302, 200)  # 2nd: no error page
    from decimal import Decimal
    with app.app_context():
        assert SessionLocal().query(Expense).filter(Expense.amount == Decimal("5200")).count() == 1


def test_both_others_owe_the_payer(client, app):
    ids = _seed_people(app)
    client.post("/login", data={"pin": "222"})  # Люда pays
    client.post("/expense", data={"amount": "60", "category": "Другое",
        "participant": [ids["Сэм"], ids["Люда"], ids["Микита"]],
        "spent_on": "2026-06-05", "request_id": "a-1"})
    from decimal import Decimal
    from app.db import SessionLocal
    from app.ledger import load_ledger
    with app.app_context():
        _people, pw = load_ledger(SessionLocal())
        assert pw[(ids["Сэм"], ids["Люда"])] == Decimal("20.00")
        assert pw[(ids["Микита"], ids["Люда"])] == Decimal("20.00")  # not zero!


def test_exclude_person_from_split(client, app):
    ids = _seed_people(app)
    client.post("/login", data={"pin": "222"})  # Люда pays, Сэм excluded
    client.post("/expense", data={"amount": "60", "category": "Другое",
        "participant": [ids["Люда"], ids["Микита"]], "spent_on": "2026-06-05", "request_id": "x-1"})
    from app.db import SessionLocal
    from app.models import Expense, ExpenseShare
    with app.app_context():
        s = SessionLocal()
        e = s.query(Expense).filter_by(request_id="x-1").first()
        pids = {sh.person_id for sh in s.query(ExpenseShare).filter_by(expense_id=e.id)}
        assert ids["Сэм"] not in pids
        assert pids == {ids["Люда"], ids["Микита"]}


def test_person_filter(client, app):
    ids = _login(client, app)  # Сэм
    client.post("/expense", data={"amount": "10", "title": "sambuy", "category": "Другое",
        "participant": [ids["Сэм"]], "spent_on": "2026-06-05", "request_id": "pf-1"})
    assert "sambuy" not in client.get(f"/?person={ids['Люда']}").get_data(as_text=True)
    assert "sambuy" in client.get(f"/?person={ids['Сэм']}").get_data(as_text=True)


def test_search_filters_feed(client, app):
    ids = _login(client, app)
    client.post("/expense", data={"amount": "10", "title": "feedmilk", "category": "Продукты",
        "participant": [ids["Сэм"]], "spent_on": "2026-06-05", "request_id": "s-1"})
    client.post("/expense", data={"amount": "20", "title": "feedbread", "category": "Продукты",
        "participant": [ids["Сэм"]], "spent_on": "2026-06-05", "request_id": "s-2"})
    page = client.get("/?q=feedmilk").get_data(as_text=True)
    assert "feedmilk" in page and "feedbread" not in page


def test_month_default_and_nav(client, app):
    from datetime import date, timedelta
    ids = _login(client, app)
    today = date.today()
    prev = today.replace(day=1) - timedelta(days=1)
    client.post("/expense", data={"amount": "10", "title": "feedcur", "category": "Другое",
        "participant": [ids["Сэм"]], "spent_on": today.isoformat(), "request_id": "m-1"})
    client.post("/expense", data={"amount": "10", "title": "feedold", "category": "Другое",
        "participant": [ids["Сэм"]], "spent_on": prev.isoformat(), "request_id": "m-2"})
    home = client.get("/").get_data(as_text=True)
    assert "feedcur" in home and "feedold" not in home  # default = current month only
    old = client.get(f"/?month={prev.year}-{prev.month:02d}").get_data(as_text=True)
    assert "feedold" in old and "feedcur" not in old


def test_empty_amount_returns_422_not_500(client, app):
    ids = _login(client, app)
    r = client.post("/expense", data={"amount": "", "participant": [ids["Сэм"]],
        "spent_on": "2026-06-05", "request_id": "e-1"})
    assert r.status_code == 422
    assert "сумма" in r.get_data(as_text=True).lower()


def test_comma_amount_accepted(client, app):
    ids = _login(client, app)
    r = client.post("/expense", data={"amount": "20,50", "title": "x", "category": "Другое",
        "participant": [ids["Сэм"]], "spent_on": "2026-06-05", "request_id": "c-1"})
    assert r.status_code in (302, 200, 204)
    from decimal import Decimal
    from app.db import SessionLocal
    from app.models import Expense
    with app.app_context():
        assert SessionLocal().query(Expense).filter_by(request_id="c-1").first().amount == Decimal("20.50")


def test_pwa_assets_served(client):
    for path in ("/static/manifest.webmanifest", "/static/sw.js",
                 "/static/styles.css", "/static/app.js",
                 "/static/icon-192.png", "/static/icon-512.png"):
        assert client.get(path).status_code == 200, path
