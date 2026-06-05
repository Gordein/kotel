# Хостинг «Котла» (бесплатно)

Это Python (Flask) + SQLite-файл. **Cloudflare Pages/Workers не подходят** — там
JS-serverless без постоянного диска. Нужен хост, где живёт процесс и файл БД. Варианты,
которые реально бесплатны:

## 1. PythonAnywhere (проще всего, бесплатно, всегда онлайн) — рекомендую

1. Зарегистрируйся на pythonanywhere.com (Beginner — free).
2. **Files** или **Bash console**: положи проект (git clone или загрузи zip).
   Приватный репозиторий: проще загрузить zip или временно сделать публичным.
3. В Bash-консоли:
   ```
   cd kotel
   python3.10 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   KOTEL_DB=$HOME/kotel/kotel.db .venv/bin/python -m flask --app wsgi init-db
   ```
4. **Web** → *Add a new web app* → *Manual configuration* → Python 3.10.
   - Virtualenv: `/home/<user>/kotel/.venv`
   - Отредактируй WSGI-файл:
     ```python
     import os, sys
     sys.path.insert(0, "/home/<user>/kotel")
     os.environ["SECRET_KEY"] = "ПОМЕНЯЙ_МЕНЯ"
     os.environ["KOTEL_DB"] = "/home/<user>/kotel/kotel.db"
     from wsgi import app as application
     ```
5. **Reload**. Приложение на `https://<user>.pythonanywhere.com` — HTTPS, ставится как PWA.
   (Free-аккаунт раз в ~3 месяца просит зайти и продлить — приложение не «засыпает».)

## 2. Oracle Cloud Always-Free VM (бесплатно навсегда, чуть сложнее)

Бесплатная ВМ (Ampere ARM). На ней:
```
docker build -t kotel .
docker run -d --restart unless-stopped -p 80:8080 \
  -v kotel_data:/data -e SECRET_KEY=ПОМЕНЯЙ_МЕНЯ kotel
```
HTTPS — через Caddy или Cloudflare перед портом 80.

## 3. Дома + Cloudflare Tunnel (0₽, без сервера)

Раз уж вы живёте вместе — запусти на любом всегда-включённом компе/мини-ПК и открой наружу:
```
.venv\Scripts\python.exe -m flask --app wsgi run --host 0.0.0.0 --port 8000
cloudflared tunnel --url http://localhost:8000
```
`cloudflared` даст бесплатный публичный HTTPS-адрес — заходите с телефонов откуда угодно.
Только для LAN (дома) хватит и просто `http://<IP-компа>:8000`.

## Перед публичным запуском
- Задай **SECRET_KEY** (иначе сессии небезопасны).
- Смени PIN'ы (по умолчанию 111/222/333) — пока через пересоздание БД: удали `kotel.db*` и `init-db`.
