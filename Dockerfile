# Explizite Version + Slim-Image
FROM python:3.12-slim

# Systemabhängigkeiten (falls nötig, z. B. für psycopg2, Pillow)
RUN apt-get update && apt-get install -y libpq-dev libjpeg-dev ffmpeg && rm -rf /var/lib/apt/lists/*

# Nicht-privilegierter Benutzer
RUN adduser --disabled-password --gecos "" appuser
WORKDIR /app
RUN chown appuser:appuser /app

# Ensure the .env file exists in the correct path or adjust the path accordingly
COPY videoflix_backend_app/.env /app/.env

# Pakete installieren (mit Cache)
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Code kopieren (mit .dockerignore)
COPY --chown=appuser:appuser . .

# Als nicht-privilegierter Benutzer ausführen
USER appuser

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]