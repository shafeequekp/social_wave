#!/bin/sh
set -e

MAX_RETRIES=30
RETRY_INTERVAL=2

echo "Waiting for database..."
attempt=1
while [ "$attempt" -le "$MAX_RETRIES" ]; do
  if uv run python -c "
import sys
from sqlalchemy import create_engine, text
from app.config.settings import settings

url = settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql+psycopg2://')
try:
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception:
    sys.exit(1)
"; then
    echo "Database is ready."
    break
  fi
  echo "Database not ready (attempt ${attempt}/${MAX_RETRIES})..."
  attempt=$((attempt + 1))
  sleep "$RETRY_INTERVAL"
done

if [ "$attempt" -gt "$MAX_RETRIES" ]; then
  echo "Database did not become ready in time."
  exit 1
fi

echo "Running migrations..."
attempt=1
while [ "$attempt" -le "$MAX_RETRIES" ]; do
  if uv run alembic upgrade head; then
    echo "Migrations complete."
    break
  fi
  echo "Migration failed (attempt ${attempt}/${MAX_RETRIES}), retrying..."
  attempt=$((attempt + 1))
  sleep "$RETRY_INTERVAL"
done

if [ "$attempt" -gt "$MAX_RETRIES" ]; then
  echo "Migrations failed after ${MAX_RETRIES} attempts."
  exit 1
fi

WORKERS="${UVICORN_WORKERS:-1}"
exec uv run uvicorn app.app:app --host 0.0.0.0 --port 8000 --workers "$WORKERS"
