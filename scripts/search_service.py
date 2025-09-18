# search_service.py
# 질의 → (로컬 임베딩 캐시 조회) → 미스 시 DataService 호출 → 결과 저장(JSONL)
from typing import List, Dict
from scripts.config import *
from scripts.data_service import DataService
from scripts.embedding_service import EmbeddingService
import json, math, os

def _cos_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)) or 1e-9
    nb = math.sqrt(sum(y*y for y in b)) or 1e-9
    return dot / (na * nb)

class _VecCache:
    def __init__(self, path: str, max_items: int):
        self.path = path
        self.max = max_items
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        # 파일 없으면 생성
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f: pass

    def _iter(self):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: yield json.loads(line)
                except Exception: continue

    def search(self, qvec: list[float], top_k=1) -> list[dict]:
        scored = []
        for obj in self._iter():
            vec = obj.get("embedding")
            if not isinstance(vec, list): continue
            sim = _cos_sim(qvec, vec)
            scored.append((sim, obj))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [o for _, o in scored[:top_k]]

    def add(self, query: str, embedding: list[float], cards: list[dict]) -> None:
        # 용량 관리: 초과분 앞부분 삭제
        rows = list(self._iter())
        rows.append({"query": query, "embedding": embedding, "cards": cards})
        if len(rows) > self.max:
            rows = rows[-self.max:]
        with open(self.path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

class SearchService:
    """임베딩 캐시 → 미스 시 DataService 조회"""
    def __init__(self):
        self.data_svc = DataService()
        self.embedder = EmbeddingService()
        self.cache    = _VecCache(VECTOR_CACHE_PATH, MAX_CACHE_ITEMS)

    def search(self, query: str, top_k: int = None) -> List[Dict]:
        want = top_k or NUM_RECOMMEND
        # 1) 캐시 조회
        qv = self.embedder.embed([query])[0]
        hits = self.cache.search(qv, top_k=1)
        if hits:
            sim = _cos_sim(qv, hits[0]["embedding"])
            if sim >= CACHE_SIM_THRESHOLD:
                cards = hits[0].get("cards") or []
                return cards[:want]
        # 2) 미스 → API 조회 후 저장
        cards = self.data_svc.recommend_items(query, want=want)
        if cards:
            self.cache.add(query, qv, cards)
        return cards
