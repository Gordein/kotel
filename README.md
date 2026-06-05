# Котёл

Сплиттер расходов на квартиру для троих (Сэм, Люда, Микита), валюта **zł**.
Flask + HTMX + Alpine + SQLite, устанавливается как PWA. Дизайн в стиле Claude.

## Что умеет
- Профили с входом по PIN (без email/паролей), PWA запоминает телефон.
- Траты с делёжкой: кто платил (один или несколько) и на кого делим (любое подмножество).
- Шаблон «Аренда» в один тап (наём+коммуналка, две руки оплаты, чек-лист переводов Михалу).
- Баланс «кто кому должен сейчас» + минимальные переводы + граф-треугольник.
- Закрытие долгов (нал/перевод), общая лента событий, комментарии.
- Защита от потери данных: неизменяемые записи, баланс на чтении, оптимистичная
  блокировка правок, idempotency-ключ, SQLite WAL.

## Запуск (Windows)

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
set SECRET_KEY=change-me
.venv\Scripts\python.exe -m flask --app wsgi init-db      # таблицы + 3 профиля (PIN 0000) + шаблон аренды
.venv\Scripts\python.exe -m flask --app wsgi run --port 8000
```

Открой http://localhost:8000 — войди (PIN у всех `0000`), смени PIN в «Профиле».
Чтобы зайти с телефонов в той же сети: `... run --host 0.0.0.0 --port 8000` и
открой `http://<IP-компа>:8000`, затем «Добавить на экран» → установится как приложение.

## Тесты

```bash
.venv\Scripts\python.exe -m pytest -q
```

## Иконки
`app/static/icon-*.png` сгенерированы `scripts/make_icons.py` (нужен Pillow, только для пересборки).

## Документы
- Дизайн: `docs/superpowers/specs/2026-06-05-kotel-design.md`
- План: `docs/superpowers/plans/2026-06-05-kotel-implementation.md`
