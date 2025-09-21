# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
import faiss
from pathlib import Path
import os, time, traceback

app = FastAPI(title="Day07 RAG QA Demo")

load_dotenv()

# 讀取 .env 檔案裡面的環境變數
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPEN_API_KEY，請檢察環境變數！")

# ------- 基本設定 -------
# 避免請求卡住：設定 OpenAI 逾時與不重試
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "20"))
client = OpenAI(timeout=OPENAI_TIMEOUT, max_retries=0)

# CORS（local開發先放寬；上線要改白名單）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------- 前端頁面顯示 -------
# <repo>/
#   backend/main.py
#   frontend/index.html
BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

# 讓根路徑直接回傳前端頁面
@app.get("/")
def root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"error": "frontend/index.html not found"}, status_code=404)

# 之後要放 js/css 圖片可用 /_static
app.mount("/_static", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# healthcheck
@app.get("/healthz")
def healthz():
    return {"ok": True}

# ------- 模擬知識庫與索引(這邊可以自行擴充) -------
docs = [
    "請假流程：需要先主管簽核，然後到 HR 系統提交。",
    "加班申請：需事先提出，加班工時可折換補休。",
    "報銷規則：需要提供發票，金額超過 1000 需經理簽核。",
    "出差申請：需填寫出差單，並附上行程與預算，送交主管審核。",
    "電腦設備申請：新進員工需向 IT 部門提出申請，並由主管批准。",
    "VPN 使用：連接公司內網必須使用公司發放的 VPN 帳號。",
    "考勤規則：遲到超過 15 分鐘需填寫說明單。",
    "文件管理：重要檔案需存放於公司雲端硬碟，不可存個人電腦。",
    "安全規範：不得將公司機密資料外傳或存放於私人雲端。",
    "年度健檢：每位員工需於 9 月前完成公司指定醫院的健康檢查。"
]

def get_embedding(text: str):
    return client.embeddings.create(
        model="text-embedding-3-small", input=text
    ).data[0].embedding

# L2 距離索引
d = 1536
index = faiss.IndexFlatL2(d)
doc_embeddings = [get_embedding(doc) for doc in docs]
index.add(np.array(doc_embeddings).astype("float32"))

# 推薦把門檻放寬，避免常常判定沒有（1.5 ~ 2.0 都可以）
L2_THRESHOLD = float(os.getenv("L2_THRESHOLD", "1.8"))

@app.get("/ask")
def ask(q: str = Query(..., description="你的問題")):
    start = time.time()
    try:
        print(f"[ask] q={q}")
        q_emb = np.array([get_embedding(q)]).astype("float32")
        D, I = index.search(q_emb, k=3)  # 取三筆較穩

        best_idx = int(I[0][0])
        best_dist = float(D[0][0])

        if best_dist > L2_THRESHOLD:
            context = "知識庫裡沒有相關答案。"
        else:
            context = docs[best_idx]

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個企業 FAQ 助理。"},
                {"role": "user", "content": f"根據以下知識庫內容回答：\n{context}\n\n問題：{q}"},
            ],
            temperature=0.2,
        )
        answer = resp.choices[0].message.content
        return {"question": q, "context": context, "answer": answer, "debug": {"l2": best_dist}}
    except Exception as e:
        traceback.print_exc()
        # 回 500，讓前端顯示錯誤並關閉 loading
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        dur = time.time() - start
        print(f"[ask] done in {dur:.2f}s")

# 直接 python3 backend/main.py 可啟動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
