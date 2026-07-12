"""서비스 계층에서 공유하는 데이터 구조 정의.

런타임 동작(그리고 JSON 직렬화 결과)을 그대로 유지하기 위해 실제 값은 평범한
`dict`로 다루고, 여기서는 형태를 문서화하는 `TypedDict`만 제공한다. 프런트엔드가
소비하는 카드/코스 스키마의 키가 곧 API 계약이므로 변경하지 않는다.
"""

from __future__ import annotations

from typing import Optional, TypedDict


class CardMetadata(TypedDict, total=False):
    """추천 카드에 딸려 나가는 원본 TourAPI 메타데이터."""
    contentid: str
    cat1: str
    addr1: str
    firstimage2: str
    title: str
    region: str
    mapx: Optional[float]
    mapy: Optional[float]
    areacode: Optional[str]
    sigungucode: Optional[str]
    contenttypeid: Optional[str]


class TourCard(TypedDict):
    """`/scripts/chat`·`/scripts/chat_stream`이 반환하는 관광지 추천 카드."""
    name: str
    reason: str
    address: str
    image_url: str
    homepage: str
    map_url: str
    metadata: CardMetadata


class CourseCard(TypedDict):
    """`/scripts/courses`가 반환하는 관광 코스 카드."""
    title: str
    thumbnail: str
    link: str
    desc: str
