FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV KOTEL_DB=/data/kotel.db
EXPOSE 8080

# Creates tables + seeds people/template on first run, then serves with waitress.
CMD ["sh", "-c", "python -m flask --app wsgi init-db && waitress-serve --listen=0.0.0.0:8080 wsgi:app"]
