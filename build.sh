#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static assets via WhiteNoise..."
python manage.py collectstatic --noinput

echo "==> Applying database migrations..."
if [ -n "$DATABASE_URL" ]; then
    python manage.py migrate --noinput || echo "Build-time migration failed or skipped (may require direct connection)."
else
    echo "DATABASE_URL not set; skipping migrate at build time."
fi

echo "==> Build completed successfully."
