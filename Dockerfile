FROM python:3.12-slim
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 openssl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN adduser --disabled-password --gecos "" --uid 10001 aistudio \
    && mkdir -p /app/data \
    && chown -R aistudio:aistudio /app/data
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AISTUDIO_HOST=0.0.0.0
ENV AISTUDIO_PORT=8123
ENV AISTUDIO_DATA=/app/data
USER aistudio
EXPOSE 8123
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8123/api/ready', timeout=3)"
CMD ["python", "-m", "product"]
