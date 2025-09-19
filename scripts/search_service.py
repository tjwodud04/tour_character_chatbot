# search_service.py
# 질의 → (Redis 임베딩 캐시 조회) → 미스 시 DataService 호출 → 결과 저장(Redis)
from typing import List, Dict, Optional
from scripts.config import *
from scripts.data_service import DataService
from scripts.embedding_service import EmbeddingService
import json, math, hashlib
import redis

def _cos_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)) or 1e-9
    nb = math.sqrt(sum(y*y for y in b)) or 1e-9
    return dot / (na * nb)

class _RedisVecCache:
    def __init__(self, redis_url: str, ttl_seconds: int):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl_seconds
        self.prefix = f"tour_cache:{CACHE_VERSION}:"

    def _make_key(self, query: str) -> str:
        # 쿼리를 해시로 변환하여 키 생성
        hash_obj = hashlib.md5(query.encode('utf-8'))
        return f"{self.prefix}{hash_obj.hexdigest()}"

    def search(self, query: str, qvec: list[float]) -> Optional[dict]:
        """쿼리와 가장 유사한 캐시 엔트리 검색"""
        try:
            # 정확한 쿼리 매치부터 시도
            key = self._make_key(query)
            cached = self.redis_client.get(key)
            if cached:
                data = json.loads(cached)
                # 임베딩 벡터 유사도 확인
                cached_vec = data.get("embedding", [])
                if cached_vec:
                    sim = _cos_sim(qvec, cached_vec)
                    if sim >= CACHE_SIM_THRESHOLD:
                        return data

            # 전체 캐시에서 유사한 벡터 검색 (옵션)
            # 성능상 이유로 일단 정확한 매치만 사용
            return None
        except Exception as e:
            print(f"Redis 캐시 검색 오류: {e}")
            return None

    def add(self, query: str, embedding: list[float], cards: list[dict]) -> None:
        """캐시에 새 엔트리 추가"""
        try:
            key = self._make_key(query)
            data = {
                "query": query,
                "embedding": embedding,
                "cards": cards,
                "timestamp": __import__('time').time()
            }
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(data, ensure_ascii=False)
            )
        except Exception as e:
            print(f"Redis 캐시 저장 오류: {e}")

class SearchService:
    """Redis 임베딩 캐시 → 미스 시 DataService 조회"""
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = (openai_api_key or "").strip()
        # EmbeddingService에 키를 주입
        self.embedder = EmbeddingService(api_key=self.openai_api_key)
        # Redis 캐시 초기화
        self.cache = _RedisVecCache(REDIS_URL, CACHE_TTL_SECONDS)

    def search(
        self,
        query: str,
        top_k: int = None,
        tour_api_key: str = None,
        openai_api_key: Optional[str] = None,
    ) -> List[Dict]:
        want = top_k or NUM_RECOMMEND

        # 1) 임베딩 벡터 생성
        qv = self.embedder.embed([query])[0]

        # 2) Redis 캐시 조회
        cached_data = self.cache.search(query, qv)
        if cached_data:
            cards = cached_data.get("cards") or []
            return cards[:want]

        # 3) 캐시 미스 → API 조회 후 저장
        api_key = (openai_api_key or self.openai_api_key or "").strip()
        data_svc = DataService(openai_api_key=api_key)
        cards = data_svc.recommend_items(query, want=want, tour_api_key=tour_api_key)

        # 4) 결과를 Redis에 캐시
        if cards:
            self.cache.add(query, qv, cards)

        return cards
