"""문장 임베딩 생성 서비스 (OpenAI Embeddings)."""

import os
from typing import List, Optional

from openai import AuthenticationError, OpenAI  # OpenAI v1+ 클라이언트

from scripts.config import OPENAI_EMBEDDING_MODEL


class EmbeddingService:
    """문자열 리스트를 임베딩 벡터 리스트로 변환한다."""

    def __init__(self, api_key: Optional[str] = None):
        # 헤더로 들어온 키 > 환경변수 순으로 사용
        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not key:
            # 상위에서 401 등으로 변환 처리하기 쉽도록 명확히 실패시킴
            raise AuthenticationError("OPENAI_API_KEY가 설정되지 않았습니다. (헤더 X-API-KEY 또는 환경변수)")
        self.client = OpenAI(api_key=key)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """문자열 리스트 → 임베딩 벡터 리스트."""
        resp = self.client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in resp.data]
