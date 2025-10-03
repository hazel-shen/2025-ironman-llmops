FROM python:3.11-slim

WORKDIR /app

# 安裝系統工具（可選：如要用 curl 當 healthcheck）
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 建立 logs 目錄並設定權限
RUN mkdir -p /app/logs && chmod 755 /app/logs

COPY app /app

# 預設只開 1 個 worker，避免 multiprocess 的 metrics 衝突（demo 環境）
CMD gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w 1 \
    -b 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    app:app

