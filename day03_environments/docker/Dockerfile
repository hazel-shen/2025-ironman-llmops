FROM continuumio/miniconda3:23.5.2-0

# ── 基本設定 ────────────────────────────────────────────────
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 可用 MODE=dev 啟用 --reload；預設 prod
ARG MODE=prod
ENV MODE=${MODE}

# ── 安裝專案環境 ────────────────────────────────────────────
COPY env/environment.yml .
RUN conda env create -f environment.yml

# 之後的 RUN/CMD/ENTRYPOINT 都在指定環境內執行
SHELL ["conda", "run", "-n", "day03_environments", "/bin/bash", "-c"]

# ── 複製程式碼（開發時可用 volume 掛載覆蓋） ───────────────
COPY src/ ./src

# ── 對外連接埠 ─────────────────────────────────────────────
EXPOSE 8000

# ── 依據 MODE 切換啟動參數 ─────────────────────────────────
# prod: 不加 --reload；dev: 加 --reload
CMD if [ "$MODE" = "dev" ]; then \
      uvicorn --app-dir /app src.app:app --host 0.0.0.0 --port 8000 --reload; \
    else \
      uvicorn --app-dir /app src.app:app --host 0.0.0.0 --port 8000; \
    fi
