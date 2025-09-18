# embedding_service.py
from typing import List, Optional
import os

from openai import OpenAI, AuthenticationError  # OpenAI v1 클라이언트
from scripts.config import *  # OPENAI_EMBEDDING_MODEL 등 사용

class EmbeddingService:
    """문장 임베딩 생성 서비스."""
    def __init__(self, api_key: Optional[str] = None):
        # 헤더로 들어온 키 > 환경변수 순으로 사용
        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not key:
            # 상위에서 401 등으로 변환 처리하기 쉽도록 명확히 실패시킴
            raise AuthenticationError("OPENAI_API_KEY not provided to EmbeddingService")
        self.client = OpenAI(api_key=key)  # 클라이언트 생성

    def embed(self, texts: List[str]) -> List[List[float]]:
        """문자열 리스트 → 임베딩 벡터 리스트."""
        resp = self.client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,  # 모델명 (config에서 정의)
            input=texts
        )
        return [d.embedding for d in resp.data]  # 벡터만 추출
