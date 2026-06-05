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


def test_pwa_assets_served(client):
    for path in ("/static/manifest.webmanifest", "/static/sw.js",
                 "/static/styles.css", "/static/app.js",
                 "/static/icon-192.png", "/static/icon-512.png"):
        assert client.get(path).status_code == 200, path
