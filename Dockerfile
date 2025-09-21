# Explizite Version + Slim-Image
FROM python:3.12-slim

# Systemabhängigkeiten (für psycopg2, Pillow, ffmpeg, etc.)
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    libpq-dev \
    libjpeg-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Unprivilegierter Nutzer
RUN adduser --disabled-login --gecos "" appuser
WORKDIR /app

# Requirements zuerst (bessere Layer-Caches)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code kopieren (achte auf .dockerignore)
COPY --chown=appuser:appuser . .

# Verzeichnisse für statics/uploads vorbereiten (wichtig bei named volumes)
RUN mkdir -p /app/staticfiles /app/uploads \
    && chown -R appuser:appuser /app

# Nicht-privilegierter Benutzer
USER appuser

# Kein CMD hier – wird von docker-compose "command:" gesetzt
