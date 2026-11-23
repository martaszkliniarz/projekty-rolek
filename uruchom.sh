#!/bin/sh
# Uruchomienie programu na Macu / Linuksie:  ./uruchom.sh
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Pierwsze uruchomienie — instaluję program…"
  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
  [ -f .env ] || cp .env.example .env
  .venv/bin/python manage.py migrate
  echo "Utwórz swoje konto (login i hasło):"
  .venv/bin/python manage.py createsuperuser
fi
.venv/bin/python manage.py migrate --noinput
(sleep 2; open http://127.0.0.1:8000/ 2>/dev/null || xdg-open http://127.0.0.1:8000/ 2>/dev/null) &
.venv/bin/python manage.py runserver 127.0.0.1:8000
