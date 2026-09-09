# popotte — une image, un conteneur, un fichier SQLite.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POPOTTE_DATA_DIR=/data \
    TZ=Europe/Paris

# tzdata : sans lui, l'image reste en UTC et les listes de courses seraient
# datées à la mauvaise heure. TZ est surchargeable par le fichier .env.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY wsgi.py .

# Le volume contient la base SQLite et les photos : sauvegarder = copier /data.
RUN useradd --create-home --uid 1000 popotte \
    && mkdir -p /data \
    && chown -R popotte:popotte /data /app
USER popotte
VOLUME ["/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"

# 2 workers suffisent largement pour un usage mono-foyer ; SQLite est en WAL.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", \
     "--timeout", "60", "--access-logfile", "-", "wsgi:app"]
