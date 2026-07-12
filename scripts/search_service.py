"""질의 → (질의 임베딩) → DataService 조회로 관광지 카드를 얻는 서비스.

현재는 벡터 캐시/재랭킹이 없어 실제 순위는 `DataService`가 결정한다. 질의 임베딩은
동일 키 검증과 향후 의미 기반 랭킹 확장을 위한 자리로 유지한다(동작 보존).
"""

from typing import List, Optional

from scripts.config import NUM_RECOMMEND
from scripts.data_service import DataService
from scripts.embedding_service import EmbeddingService
from scripts.schemas import TourCard


class SearchService:
    """DataService를 직접 조회한다(별도 벡터 캐시 없음)."""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = (openai_api_key or "").strip()
        # EmbeddingService에 키를 주입 (키 유효성도 함께 검증됨)
        self.embedder = EmbeddingService(api_key=self.openai_api_key)

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        tour_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ) -> List[TourCard]:
        want = top_k or NUM_RECOMMEND

        # 1) 질의 임베딩 생성 (현 단계에선 랭킹에 직접 쓰이지 않음)
        self.embedder.embed([query])

        # 2) DataService로 직접 조회
        api_key = (openai_api_key or self.openai_api_key or "").strip()
        data_svc = DataService(openai_api_key=api_key)
        return data_svc.recommend_items(query, want=want, tour_api_key=tour_api_key)
