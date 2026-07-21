#!/bin/sh
set -e

echo "[entrypoint] waiting for database..."
python - <<'PY'
import os, time
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
from django.db.utils import OperationalError

for i in range(30):
    try:
        connection.ensure_connection()
        print("[entrypoint] database is ready")
        break
    except OperationalError as exc:
        print(f"[entrypoint] db not ready ({i+1}/30): {exc}")
        time.sleep(2)
else:
    raise SystemExit("database connection failed")
PY

echo "[entrypoint] migrate..."
python manage.py migrate --noinput

echo "[entrypoint] collectstatic..."
python manage.py collectstatic --noinput

WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
PORT="${PORT:-8000}"

echo "[entrypoint] starting gunicorn on 0.0.0.0:${PORT}"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
