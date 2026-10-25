# Use official lightweight Python image matching verified project runtime (Python 3.13.5)
FROM python:3.13.5-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default port for Back4app Containers (fallback if PORT is unset)
ENV PORT=8080

# Set working directory
WORKDIR /app

# Install minimal system dependencies required for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from existing requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

# Collect static assets into staticfiles/ using WhiteNoise storage
# A dummy build-time secret key allows collectstatic to compile assets without requiring production credentials
RUN DJANGO_SECRET_KEY=build-time-dummy-key-for-collectstatic \
    python manage.py collectstatic --noinput

# Expose default port (metadata documentation; platform routes traffic dynamically)
EXPOSE 8080

# Health check probe matching existing /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8080}/health || exit 1

# Start Gunicorn WSGI server listening on 0.0.0.0 using dynamic $PORT
CMD ["sh", "-c", "exec gunicorn workease.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4"]
