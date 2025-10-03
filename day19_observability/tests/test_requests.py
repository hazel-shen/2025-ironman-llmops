import requests
import time

BASE_URL = "http://localhost:8000"

def call_api(model="gpt-4o-mini", question="用三點解釋 RAG"):
    resp = requests.post(
        f"{BASE_URL}/ask",
        json={
            "model": model,
            "messages": [{"role": "user", "content": question}],
        },
        timeout=30,
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ {model} 回答：{data['answer'][:40]}... (tokens={data['prompt_tokens']}+{data['completion_tokens']}, cost={data['cost_usd']}$)")
    else:
        print(f"❌ 請求失敗: {resp.status_code} {resp.text}")

def show_metrics():
    resp = requests.get(f"{BASE_URL}/metrics")
    print("\n📊 Metrics 部分輸出：")
    for line in resp.text.splitlines():
        if any(key in line for key in ["llm_requests_total", "llm_tokens_total", "llm_cost_usd_total"]):
            print(line)

if __name__ == "__main__":
    # 打幾次請求
    call_api(question="請給我一句勵志名言")
    call_api(question="Explain RAG in 2 sentences")
    call_api(model="gpt-4o", question="金融業裡 RAG 的應用")
    
    # 稍等一下
    time.sleep(2)
    # 印 metrics
    show_metrics()
