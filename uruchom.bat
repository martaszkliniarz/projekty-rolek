@echo off
REM Uruchomienie programu na komputerze z Windows (dwuklik).
cd /d "%~dp0"
if not exist .venv (
  echo Pierwsze uruchomienie - instaluje program, to potrwa chwile...
  py -m venv .venv || python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  if not exist .env copy .env.example .env
  .venv\Scripts\python manage.py migrate
  echo.
  echo Utworz swoje konto (login i haslo):
  .venv\Scripts\python manage.py createsuperuser
)
.venv\Scripts\python manage.py migrate --noinput
start "" http://127.0.0.1:8000/
.venv\Scripts\python manage.py runserver 127.0.0.1:8000
