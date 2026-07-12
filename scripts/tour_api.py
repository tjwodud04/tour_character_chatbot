"""한국관광공사 TourAPI(KorService2) HTTP 클라이언트.

기존에 각 호출부에 흩어져 중복되던 (공통 파라미터 구성 + GET + 안전한 JSON 파싱 +
`response.body.items.item` 추출) 로직을 한 곳으로 모은다. 비즈니스 로직(요약/필터/
카드 구성)은 상위 `DataService`가 담당하고, 이 클라이언트는 원본 아이템만 돌려준다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import requests

from scripts.config import (
    KOREA_TOURISM_API_BASE,
    KOREA_TOURISM_API_KEY,
    TOURAPI_ARRANGE_IMAGE_FIRST,
    TOURAPI_MOBILE_APP,
    TOURAPI_MOBILE_OS,
    TOURAPI_RESPONSE_TYPE,
    TOURAPI_TIMEOUT,
)


def _normalize_service_key(raw: str) -> str:
    """서비스 키를 정규화한다: URL 인코딩 해제 후 공백 제거."""
    key = (raw or "").strip()
    if "%" in key:
        key = unquote(key)
    return key.replace(" ", "")


class TourAPIClient:
    """TourAPI 엔드포인트별 원본 아이템 목록을 반환하는 얇은 HTTP 래퍼."""

    def __init__(
        self,
        service_key: Optional[str] = None,
        base_url: str = KOREA_TOURISM_API_BASE,
        timeout: int = TOURAPI_TIMEOUT,
    ):
        self.service_key = service_key or KOREA_TOURISM_API_KEY
        self.base_url = base_url
        self.timeout = timeout

    # --- 내부 헬퍼 -------------------------------------------------------------
    def _common_params(self, service_key: Optional[str], rows: int, page: int = 1) -> Dict[str, Any]:
        """모든 요청에 공통으로 들어가는 파라미터 묶음."""
        return {
            "serviceKey": _normalize_service_key(service_key or self.service_key or ""),
            "numOfRows": rows,
            "pageNo": page,
            "MobileOS": TOURAPI_MOBILE_OS,
            "MobileApp": TOURAPI_MOBILE_APP,
            "_type": TOURAPI_RESPONSE_TYPE,
        }

    @staticmethod
    def _safe_json(resp: requests.Response) -> dict:
        """JSON 응답만 파싱하고, 그렇지 않으면 진단 정보와 함께 예외를 던진다."""
        ctype = (resp.headers.get("Content-Type") or "").lower()
        text = (resp.text or "").strip()
        if "json" in ctype or (text and (text.startswith("{") or text.startswith("["))):
            try:
                return resp.json()
            except Exception:
                pass
        head = text[:300].replace("\n", " ") if text else ""
        raise ValueError(f"Non-JSON response (status={resp.status_code}, ct='{ctype}'). Body head: {head}")

    @staticmethod
    def _extract_items(payload: dict) -> List[Dict]:
        """`response.body.items.item`을 항상 리스트로 정규화해서 반환한다."""
        items = (
            payload.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        ) or []
        if isinstance(items, dict):
            return [items]
        return items if isinstance(items, list) else [items]

    def _get_items(self, endpoint: str, params: Dict[str, Any]) -> List[Dict]:
        """`endpoint`를 GET 하고 아이템 리스트를 반환한다. 오류 시 빈 리스트."""
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return self._extract_items(self._safe_json(resp))
        except Exception as exc:
            print(f"[TourAPI] {endpoint} 호출 오류: {exc}")
            return []

    # --- 엔드포인트 -----------------------------------------------------------
    def search_keyword(self, keyword: str, rows: int = 3, service_key: Optional[str] = None) -> List[Dict]:
        """searchKeyword2: 키워드로 관광지 후보를 검색한다."""
        params = self._common_params(service_key, rows)
        params["keyword"] = (keyword or "").strip()
        return self._get_items("searchKeyword2", params)

    def area_codes(self, rows: int = 100, service_key: Optional[str] = None) -> List[Dict]:
        """areaCode2: 광역 지역 코드 목록을 조회한다."""
        return self._get_items("areaCode2", self._common_params(service_key, rows))

    def detail_common(self, content_id: str, service_key: Optional[str] = None) -> Optional[Dict]:
        """detailCommon2: 콘텐츠 상세(개요/홈페이지/좌표) 원본 아이템 1건."""
        if not content_id:
            return None
        params = self._common_params(service_key, rows=1)
        params["contentId"] = content_id
        items = self._get_items("detailCommon2", params)
        return items[0] if items else None

    def detail_image(self, content_id: str, service_key: Optional[str] = None) -> List[Dict]:
        """detailImage2: 콘텐츠 추가 이미지 목록."""
        if not content_id:
            return []
        params = self._common_params(service_key, rows=1)
        params["contentId"] = content_id
        return self._get_items("detailImage2", params)

    def area_based_list(
        self,
        *,
        rows: int,
        area_code: Optional[str] = None,
        sigungu_code: Optional[str] = None,
        cat1: Optional[str] = None,
        content_type_id: Optional[str] = None,
        arrange: str = TOURAPI_ARRANGE_IMAGE_FIRST,
        service_key: Optional[str] = None,
    ) -> List[Dict]:
        """areaBasedList2: 지역/카테고리 기반 관광지 목록(대표이미지 보장 정렬)."""
        params = self._common_params(service_key, rows)
        params["arrange"] = arrange
        if area_code:
            params["areaCode"] = area_code
        if sigungu_code:
            params["sigunguCode"] = sigungu_code
        if cat1:
            params["cat1"] = cat1
        if content_type_id:
            params["contentTypeId"] = content_type_id
        return self._get_items("areaBasedList2", params)
