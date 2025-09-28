#!/usr/bin/env python3
"""
scripts/watch_and_trigger.py
監控 data/worker_manual.txt；一旦檔案被修改，立即觸發 RAG pipeline。

兩種觸發模式（二選一）：
- 本機直接跑 Flow（預設）：import flows.daily_pipeline 後呼叫 daily_pipeline()
- 觸發 Prefect Deployment：設 USE_PREFECT_DEPLOYMENT=true → run_deployment()

環境變數（可選）：
- USE_PREFECT_DEPLOYMENT=true/false       # 預設 false（本機直接跑 Flow）
- PREFECT_DEPLOYMENT_NAME=daily_rag_update/daily-2am
- DEBOUNCE_SEC=2                          # 去彈跳秒數，避免儲存多次觸發
- WATCH_FILE=data/worker_manual.txt       # 自訂監看的檔案路徑（相對於專案根）

使用方式：
    pip install watchdog
    python scripts/watch_and_trigger.py
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# ── 讓腳本在 scripts/ 下執行也能 import 專案內模組 ────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from watchdog.events import FileSystemEventHandler  # type: ignore
from watchdog.observers import Observer  # type: ignore

# 環境設定
USE_DEPLOYMENT = os.getenv("USE_PREFECT_DEPLOYMENT", "false").lower() in {"1", "true", "yes"}
DEPLOYMENT_NAME = os.getenv("PREFECT_DEPLOYMENT_NAME", "daily_rag_update/daily-2am")
DEBOUNCE_SEC = float(os.getenv("DEBOUNCE_SEC", "2"))
WATCH_FILE = os.getenv("WATCH_FILE", "data/worker_manual.txt")

TARGET = (ROOT / WATCH_FILE).resolve()

print(f"👀 Watch file: {TARGET}")
print(f"⚙️  Trigger mode: {'Prefect Deployment' if USE_DEPLOYMENT else 'Local Flow'}")
if USE_DEPLOYMENT:
    print(f"   Deployment: {DEPLOYMENT_NAME}")

class TriggerOnChange(FileSystemEventHandler):
    def __init__(self, target: Path, debounce_sec: float = 2.0):
        super().__init__()
        self.target = target
        self.debounce_sec = debounce_sec
        self._last_ts = 0.0
        self._last_mtime = None

    def _should_fire(self, path: Path) -> bool:
        if path.resolve() != self.target:
            return False
        now = time.monotonic()
        if now - self._last_ts < self.debounce_sec:
            return False
        try:
            mtime = self.target.stat().st_mtime
        except FileNotFoundError:
            return False
        if self._last_mtime is not None and mtime == self._last_mtime:
            return False
        self._last_mtime = mtime
        self._last_ts = now
        return True

    def on_modified(self, event):
        path = Path(event.src_path)
        if self._should_fire(path):
            trigger_pipeline()

    # 有些編輯器儲存時會走「建立臨時檔再 replace」，補監聽 created 事件
    def on_created(self, event):
        path = Path(event.src_path)
        if self._should_fire(path):
            trigger_pipeline()

def trigger_pipeline():
    if USE_DEPLOYMENT:
        # 觸發 Prefect Deployment（需要 Server/Cloud + Agent）
        from prefect.deployments import run_deployment
        print(f"⚡ Detected change → run deployment: {DEPLOYMENT_NAME}")
        try:
            asyncio.run(run_deployment(name=DEPLOYMENT_NAME))
            print("✅ Deployment triggered.")
        except Exception as e:
            print(f"❌ Failed to trigger deployment: {e}")
    else:
        # 本機直接執行 Flow（不需 Server/Agent）
        print("⚡ Detected change → run local flow: daily_pipeline()")
        try:
            from flows.daily_pipeline import daily_pipeline
            daily_pipeline()
            print("✅ Local flow finished.")
        except Exception as e:
            print(f"❌ Local flow failed: {e}")

def main():
    watch_dir = TARGET.parent
    if not TARGET.exists():
        print("⚠️  目標檔尚不存在，仍會監看目錄；建立或修改後會觸發。")

    event_handler = TriggerOnChange(TARGET, DEBOUNCE_SEC)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    observer.start()
    print(f"🟢 Watching directory: {watch_dir} (debounce={DEBOUNCE_SEC}s)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
