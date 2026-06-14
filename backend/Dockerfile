FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

RUN groupadd -r appuser && \
    useradd --no-log-init -r -g appuser -d $HOME -s /usr/sbin/nologin -m appuser

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        unzip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ---- Copy app ----
COPY --chown=appuser:appuser . .

RUN chmod +x /app/docker-entrypoint.sh && \
    mkdir -p $HF_HOME /app/uploads && \
    chown -R appuser:appuser /app && \
    find /app -type d -name "__pycache__" -exec rm -rf {} + || true

# ---- Switch user ----
USER appuser

EXPOSE 8081
ENTRYPOINT ["/app/docker-entrypoint.sh"]