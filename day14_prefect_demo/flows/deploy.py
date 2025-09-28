"""
flows/deploy.py

這支程式的用途：
1. 匯入 daily_pipeline（主要的 Prefect Flow）。
2. 建立一個 Deployment，將 daily_pipeline 綁定到 Prefect 的工作排程。
3. 設定 Cron 排程：每天 02:00 (Asia/Taipei) 自動執行。
4. 指定 work_queue_name="default"，方便 Agent 撿取任務。
5. 套用 Deployment → 註冊到 Prefect Server/Cloud。
   - 之後只要有 Prefect Agent 在跑，流程就會每天 02:00 自動觸發。

流程說明：
    deploy.py → 建立 Deployment → Prefect Server 記錄排程 → Agent 撿取 → 執行 daily_pipeline

使用方式：
    python -m flows.deploy
    # 建立 Deployment 後，可用以下指令確認：
    prefect deployment ls
    # 啟動 Agent（確保有 worker 來執行 flow）：
    prefect agent start -q default
"""
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

# 相對匯入：在套件語境下正確
from .daily_pipeline import daily_pipeline

if __name__ == "__main__":
    dep = Deployment.build_from_flow(
        flow=daily_pipeline,
        name="daily-2am",
        schedule=CronSchedule(cron="0 2 * * *", timezone="Asia/Taipei"),
        work_queue_name="default",
    )
    dep.apply()
    print("✅ Deployment created: daily-2am (02:00 Asia/Taipei)")
