from typing import List, Tuple
from pathlib import Path
import json
import numpy as np
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer

from .models import ContextChunk, RetrievalSignals

class SimpleRetriever:
    """
    Jieba 分詞 + TF-IDF；kb.jsonl 每行: {"id": "doc1", "text": "..."}
    """

    def __init__(self, kb_path: str):
        self.kb_path = Path(kb_path)
        self.ids: List[str] = []
        self.texts: List[str] = []
        self._load()

        # 初始化 jieba（可選：自定詞典可用 jieba.load_userdict(...)）
        jieba.initialize()
        jieba.load_userdict("data/userdict.txt") # 自訂辭典，讓 jieba 可以切出正確的詞彙

        # 重要：tokenizer 搭配 token_pattern=None，否則 tokenizer 不會生效
        self.vectorizer = TfidfVectorizer(
            tokenizer=lambda s: list(jieba.cut(s, HMM=True)),
            token_pattern=None,
            ngram_range=(1, 2),       # 詞 + 2-gram 詞組
            max_features=20_000,
            norm="l2"
        )
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def _load(self):
        self.ids.clear()
        self.texts.clear()
        with self.kb_path.open("r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                self.ids.append(obj["id"])
                self.texts.append(obj["text"])

    def search(self, query: str, top_k: int = 3) -> Tuple[List[ContextChunk], RetrievalSignals]:
        qv = self.vectorizer.transform([query])
        # 對 TF-IDF，使用稀疏點積即可（等同於 cosine with l2 正規化）
        scores = (self.matrix @ qv.T).toarray().ravel()

        # 取前 K
        top_idx = np.argsort(-scores)[:top_k]
        chunks: List[ContextChunk] = [
            ContextChunk(id=self.ids[i], text=self.texts[i], score=float(scores[i]))
            for i in top_idx
        ]

        # 訊號
        max_score = float(scores[top_idx[0]]) if len(top_idx) else 0.0
        hits = scores[top_idx]
        pos_hits = hits[hits > 0]
        avg_topk = float(np.mean(pos_hits)) if pos_hits.size > 0 else 0.0
        num_docs = int(np.sum(scores > 0.0))
        context_len = sum(len(c.text) for c in chunks)

        signals = RetrievalSignals(
            max_score=max_score,
            avg_topk=avg_topk,
            num_docs=num_docs,
            context_len=context_len,
        )
        return chunks, signals
