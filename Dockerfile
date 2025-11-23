FROM python:3.12-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    libpq-dev \
    libjpeg-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-login --gecos "" appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .
RUN chmod +x /app/backend.entrypoint.sh /app/backend.dev.entrypoint.sh

RUN mkdir -p /app/staticfiles /app/uploads \
    && chown -R appuser:appuser /app

USER appuser
