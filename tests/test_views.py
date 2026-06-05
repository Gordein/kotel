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
            s.add_all([Person(name=n, color="#888", pin_hash=set_pin("1234"))
                       for n in ("Сэм", "Люда", "Микита")])
            s.commit()
        return {p.name: p.id for p in s.query(Person).order_by(Person.id).all()}


def _login(client, app, name="Сэм"):
    ids = _seed_people(app)
    client.post("/login", data={"person_id": ids[name], "pin": "1234"})
    return ids


def test_login_page_renders(client, app):
    _seed_people(app)
    assert client.get("/login").status_code == 200


def test_login_redirects(client, app):
    ids = _seed_people(app)
    resp = client.post("/login", data={"person_id": ids["Сэм"], "pin": "1234"})
    assert resp.status_code == 302


def test_requires_login(client, app):
    # Not logged in -> protected pages redirect to /login
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_all_screens_render(client, app):
    _login(client, app)
    for path in ("/", "/feed", "/expense/new", "/settle", "/profile"):
        assert client.get(path).status_code == 200, path


def test_create_expense_via_form(client, app):
    ids = _login(client, app)
    resp = client.post("/expense", data={
        "amount": "30", "title": "Продукты", "category": "Продукты",
        "payer_id": ids["Сэм"], "participant": [ids["Сэм"], ids["Люда"], ids["Микита"]],
        "spent_on": "2026-06-05", "request_id": "form-1"})
    assert resp.status_code in (302, 200)
    from app.db import SessionLocal
    from app.models import Expense
    with app.app_context():
        assert SessionLocal().query(Expense).filter_by(request_id="form-1").count() == 1


def test_balance_and_settlement(client, app):
    ids = _login(client, app)
    # Lyuda pays 700 for Sam only
    client.post("/expense", data={"amount": "700", "title": "X", "category": "Другое",
        "payer_id": ids["Люда"], "participant": [ids["Сэм"]], "spent_on": "2026-06-05",
        "request_id": "b-1"})
    assert client.get("/").status_code == 200
    # Sam settles 700 to Lyuda
    r = client.post("/settle", data={"to_person": ids["Люда"], "amount": "700",
        "method": "cash", "settled_on": "2026-06-05", "request_id": "set-1"})
    assert r.status_code in (302, 200)
    assert client.get("/").status_code == 200


def test_feed_loads(client, app):
    _login(client, app)
    assert client.get("/feed").status_code == 200


def test_from_template_creates_rent(client, app):
    import json
    _login(client, app)
    from app.db import SessionLocal
    from app.models import Expense, Template
    with app.app_context():
        s = SessionLocal()
        s.add(Template(title="Аренда", category="Квартира (аренда)",
                       default_payers=json.dumps({"Люда": "2600", "Микита": "2600"}),
                       default_shares=json.dumps({"Сэм": "1900", "Люда": "1900", "Микита": "1400"}),
                       note="x"))
        s.commit()
        tid = s.query(Template).first().id
    r = client.post(f"/expense/from-template/{tid}")
    assert r.status_code in (302, 200)
    from decimal import Decimal
    with app.app_context():
        assert SessionLocal().query(Expense).filter(Expense.amount == Decimal("5200")).count() == 1


def test_comment_flow(client, app):
    ids = _login(client, app)
    client.post("/expense", data={"amount": "9", "title": "X", "category": "Другое",
        "payer_id": ids["Сэм"], "participant": [ids["Сэм"]], "spent_on": "2026-06-05",
        "request_id": "cm-1"})
    from app.db import SessionLocal
    from app.models import Expense
    with app.app_context():
        eid = SessionLocal().query(Expense).filter_by(request_id="cm-1").first().id
    r = client.post(f"/item/expense/{eid}/comments", data={"text": "тест"})
    assert r.status_code in (302, 200)
    page = client.get(f"/item/expense/{eid}/comments")
    assert "тест" in page.get_data(as_text=True)


def test_pwa_assets_served(client):
    for path in ("/static/manifest.webmanifest", "/static/sw.js",
                 "/static/styles.css", "/static/app.js",
                 "/static/icon-192.png", "/static/icon-512.png"):
        assert client.get(path).status_code == 200, path

