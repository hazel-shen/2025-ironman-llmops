# Day04 Vector DB Demo

## 啟動環境

1. FAISS 驗證

```bash
# 建立環境
conda env create -f environment.yaml

# 啟動環境
conda activate day04_vector_db

# 驗證 FAISS
❯ python faiss_demo.py
```

2. weaviate 驗證

```bash
# 驗證 weaviate
cd weaviate_demo

# 啟動 Docker 容器
docker-compose up -d

# 把 Pinecone API key 寫入環境變數
echo "PINECONE_API_KEY=pcsk_XXXX(你的 Pinecone API key)" >> .env

# 執行 Demo 程式 - 插入文件
python insert_docs.py

# 執行 Demo 程式 - 查詢文件
python query_docs.py

# 結束 docker 容器，-v參數意思：連 volumes 一起刪掉（資料會消失）
docker-compose down -v
```

3. # 驗證 pinecone

```bash
python pinecone_demo.py
```
