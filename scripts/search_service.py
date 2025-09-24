# search_service.py
# 질의 → 임베딩 → DataService 호출 (캐시 없음)
from typing import List, Dict, Optional
from scripts.config import *
from scripts.data_service import DataService
from scripts.embedding_service import EmbeddingService
import json, math, hashlib

def _cos_sim(a: list[float], b: list[float]) -> float:
    """코사인 유사도 (0-division 방지 포함)"""
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)) or 1e-9
    nb = math.sqrt(sum(y*y for y in b)) or 1e-9
    return dot / (na * nb)

class SearchService:
    """직접 DataService 조회 (캐시 없음)"""
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = (openai_api_key or "").strip()
        # EmbeddingService에 키를 주입
        self.embedder = EmbeddingService(api_key=self.openai_api_key)

    def search(
        self,
        query: str,
        top_k: int = None,
        tour_api_key: str = None,
        openai_api_key: Optional[str] = None,
    ) -> List[Dict]:
        want = top_k or NUM_RECOMMEND

        # 1) 임베딩 벡터 생성 (캐시 없음)
        qv = self.embedder.embed([query])[0]

        # 2) 직접 API 조회
        api_key = (openai_api_key or self.openai_api_key or "").strip()
        data_svc = DataService(openai_api_key=api_key)
        cards = data_svc.recommend_items(query, want=want, tour_api_key=tour_api_key)

        return cards
