# embedding_service.py
from openai import OpenAI     # OpenAI v1 클라이언트
from scripts.config import *   # 설정
from typing import List       # 타입 힌트

class EmbeddingService:
    """문장 임베딩 생성 서비스."""
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)  # 클라이언트 생성

    def embed(self, texts: List[str]) -> List[List[float]]:
        """문자열 리스트 → 임베딩 벡터 리스트."""
        resp = self.client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,  # 모델명
            input=texts                            # 입력들
        )
        return [d.embedding for d in resp.data]    # 벡터만 추출
