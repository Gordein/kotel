# Котёл — сплиттер расходов на квартиру (3 соседа, zł)

Flask + HTMX + Alpine + SQLite (WAL). PWA. Не SPA. Источник истины — этот файл и
`docs/superpowers/specs/2026-06-05-kotel-design.md`.

## Принципы
- Балансы НЕ хранятся — считаются на чтении из неизменяемых записей (нет гонки на счётчике).
- Правки траты — через оптимистичную блокировку (`version`). Записи — `request_id` (idempotency).
- Удаление — мягкое (`deleted_at`). Деньги/комментарии не теряются.
- Чистая логика (`money.py`, `balances.py`) — без Flask/DB, покрыта тестами.
- Сервисы (`expenses.py`, `settlements.py`, `comments.py`, `templates_svc.py`) владеют
  записью + валидацией; views тонкие и зовут сервисы.
- Одна валюта (zł), одна квартира, без уведомлений. UI без перегруза.
- Вход **только по PIN** (PIN уникален и определяет аккаунт; чужой PIN не сбрасывается).
- Баланс **эго-центричный** — каждый видит только свои долги; граф рисует только свои рёбра.
- `ledger.py` — единая загрузка баланса из БД (для экранов «Баланс» и «Закрыть долг»).
- CLI-вывод — только ASCII (консоль Windows = cp1252). В вебе UTF-8 везде.

## Структура
```
app/
  __init__.py      app factory, регистрация blueprints, init-db CLI
  config.py db.py  конфиг + движок (WAL)
  models.py        Person, Expense(+payers/shares), Settlement, Comment, Template
  money.py         parse/format/equal-split
  balances.py      compute_balances, suggest_transfers
  auth.py          PIN, login/session, current_user, reset_pin
  expenses.py settlements.py comments.py templates_svc.py   сервисы
  feed.py          сборка ленты (derived)
  views/           blueprints: auth, balance, expense, settlement, feed, profile
  templates/ static/
tests/             pytest (домен + сервисы + рендеры + флоу)
```

## Команды
```
.venv\Scripts\python.exe -m flask --app wsgi init-db
.venv\Scripts\python.exe -m flask --app wsgi run --port 8000
.venv\Scripts\python.exe -m pytest -q
```

## Чего НЕ делать (YAGNI)
Несколько квартир, уведомления/push, мультивалюта, фото чеков, офлайн-запись,
websockets, редактирование категорий из UI, удаление/добавление людей.
