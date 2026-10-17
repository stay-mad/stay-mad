#!/bin/sh
set -e

# Run Alembic migrations if RUN_MIGRATIONS or ALEMBIC_AUTO_UPGRADE is true
if [ "${RUN_MIGRATIONS:-false}" = "true" ] || [ "${ALEMBIC_AUTO_UPGRADE:-false}" = "true" ]; then
    echo "==> Running Alembic migrations to head..."
    alembic upgrade head
    echo "==> Migrations complete."
fi

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

echo "==> Launching Stay Mad API server on http://${HOST}:${PORT}..."
# Using exec ensures uvicorn receives SIGTERM directly for Cloud Run scaling
exec uvicorn backend.staymad.api.main:app --host "${HOST}" --port "${PORT}" --lifespan on
