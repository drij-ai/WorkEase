#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static assets via WhiteNoise..."
python manage.py collectstatic --noinput

echo "==> Build completed successfully."
