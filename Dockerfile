# Explizite Version + Slim-Image
FROM python:3.12-slim

# Systemabhängigkeiten (falls nötig, z. B. für psycopg2, Pillow)
RUN apt-get update && apt-get install --no-install-recommends -y libpq-dev libjpeg-dev ffmpeg && rm -rf /var/lib/apt/lists/*

# Nicht-privilegierter Benutzer
RUN adduser --disabled-login appuser
WORKDIR /app
RUN chown -R appuser:appuser /app

# Pakete installieren (mit Cache)
WORKDIR /app
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Code kopieren (mit .dockerignore)
COPY --chown=appuser:appuser . .

# Als nicht-privilegierter Benutzer ausführen
USER appuser
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]