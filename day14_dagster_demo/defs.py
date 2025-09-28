from __future__ import annotations
from pathlib import Path
from dagster import (
    Definitions,
    AssetSelection,
    define_asset_job,
    ScheduleDefinition,
    SensorDefinition,
    RunRequest,
)

# === 匯入各資產 ===
# 每個 asset 都是獨立檔案：raw → cleaned → chunks → vectors → index
from assets.raw_text import raw_text
from assets.cleaned_text import cleaned_text
from assets.chunks import chunks
from assets.vectors import vectors
from assets.vector_index import vector_index

# === Job: 一次物化全部資產 ===
# 定義一個 job，選擇所有資產來 materialize。
# 之後可以透過 job/schedule/sensor 來觸發。
materialize_all = define_asset_job(
    name="materialize_all",
    selection=AssetSelection.all()
)

# === Schedule: 每日 02:00 Asia/Taipei 執行 ===
daily_2am = ScheduleDefinition(
    name="daily_2am_taipei",
    job=materialize_all,
    cron_schedule="0 2 * * *",  # CRON 表達式
    execution_timezone="Asia/Taipei",  # 時區
)

# === Sensor: 檔案變更觸發 pipeline ===
# 當 data/worker_manual.txt 有修改時，自動觸發 materialize_all
TARGET = Path(__file__).resolve().parent / "data" / "worker_manual.txt"

# 取得檔案最後修改時間 (mtime)
def _mtime() -> float:
    return TARGET.stat().st_mtime if TARGET.exists() else 0.0

# Sensor 主函式
def file_change_sensor_fn(context):
    last = float(context.cursor) if context.cursor else 0.0  # 上次檢查記錄的時間
    cur = _mtime()  # 目前檔案修改時間

    if cur and cur > last:  # 檔案被更新
        context.update_cursor(str(cur))  # 更新 cursor
        yield RunRequest(run_key=str(cur), run_config={})  # 觸發 materialize_all
    else:
        # 如果檔案存在但沒更新，也更新 cursor 避免重複觸發
        if cur and cur != last:
            context.update_cursor(str(cur))

file_change_sensor = SensorDefinition(
    name="on_worker_manual_change",
    evaluation_fn=file_change_sensor_fn,
    minimum_interval_seconds=2,  # 每 2 秒檢查一次
    description=f"偵測 {TARGET} 變更後觸發 materialize_all",
    target=materialize_all,
)

# === Dagster Definitions: 全部組合 ===
# - assets: 我們的 5 個資產 (raw → index)
# - schedules: 每日凌晨自動執行
# - sensors: 檔案變更自動觸發
# - jobs: 可以手動或程式呼叫
defs = Definitions(
    assets=[raw_text, cleaned_text, chunks, vectors, vector_index],
    schedules=[daily_2am],
    sensors=[file_change_sensor],
    jobs=[materialize_all],
)
