"""관광지 추천 파이프라인.

흐름: 질의 → LLM으로 지역/대분류(cat1) 1개씩 추출 → areaCode/sigunguCode 고정
(fast mapper) → areaBasedList2(대표이미지 보장 정렬) → cat1 필터 → 여행코스
(contentTypeId=25) 차단(+화이트리스트 재쿼리) → 휴리스틱 클린 → detailCommon2로
개요/홈페이지 보강(+1문장 요약) → detailImage2 폴백 → 최종 카드 스키마 반환.

TourAPI HTTP 호출은 `TourAPIClient`, 이미지 검증은 `images` 모듈에 위임하고,
이 서비스는 OpenAI 기반 추출/요약과 카드 조립(비즈니스 로직)만 담당한다.
"""

import json
import random
import re
from typing import List, Optional, Tuple

from openai import OpenAI

from scripts.config import (
    API_FETCH_MULTIPLIER,
    CAT1_CHOICES,
    COURSE_CAT1_CODE,
    COURSE_CONTENT_TYPE_ID,
    GOOGLE_MAPS_QUERY_URL_TEMPLATE,
    IMAGE_CACHE_MAX,
    IMAGE_CACHE_TTL_SEC,
    NUM_RECOMMEND,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    REGION_EXTRACT_MAX_TOKENS,
    SUMMARY_MAX_TOKENS,
    TOURAPI_LIST_MIN_ROWS,
    TOURIST_CONTENT_TYPE_WHITELIST,
)
from scripts.images import ImageCache, normalize_homepage, to_https, validate_image_url
from scripts.regions import NORMALIZE_REGION, REGION_HINTS, fast_area_sigungu
from scripts.schemas import CardMetadata, TourCard
from scripts.tour_api import TourAPIClient

# 유효한 cat1 코드 집합 (검증용)
_VALID_CAT1_CODES = {c["code"] for c in CAT1_CHOICES}


def _compose_full_address(addr1: str, addr2: str) -> str:
    """addr1/addr2를 공백으로 이어 하나의 주소 문자열을 만든다."""
    a1, a2 = (addr1 or "").strip(), (addr2 or "").strip()
    return f"{a1} {a2}".strip() if a1 and a2 else (a1 or a2 or "")


class DataService:
    """OpenAI로 (region, cat1) 추출 → 지역코드화 → TourAPI 목록/상세 → 카드 스키마 생성."""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.tour = TourAPIClient()
        self._img_cache = ImageCache(IMAGE_CACHE_TTL_SEC, IMAGE_CACHE_MAX)
        api_key = openai_api_key or OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.client = OpenAI(api_key=api_key)

    # --- 키워드로 areaCode 힌트 추출 (옵션) ---
    def _area_hint_from_keyword(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        if not (query or "").strip():
            return None, None
        for item in self.tour.search_keyword(query.strip(), rows=3):
            area_code = str(item.get("areacode") or item.get("areaCode") or "").strip() or None
            sigungu_code = str(item.get("sigungucode") or item.get("sigunguCode") or "").strip() or None
            if area_code:
                return area_code, sigungu_code
        return None, None

    # --- 1) (region, cat1) 추출  ※여기서 'C01 기본 금지' 규칙을 프롬프트에 못박음 ---
    def _extract_region_and_cat1(self, user_query: str) -> Tuple[str, Optional[str]]:
        try:
            cat_list = "\n".join([f"- {c['code']} : {c['name']}" for c in CAT1_CHOICES])
            prompt = f"""
다음 한국어 요청에서
1) 정확한 지역명 1개 (시/도/광역시/특별시 또는 시/군 단위)
2) 아래 목록 중 가장 가까운 대분류 cat1 코드 1개
를 JSON으로만 출력하세요.

규칙:
- 사용자가 '코스/일정/루트/동선/투어'를 명시한 경우에만 cat1=C01(추천코스)을 선택한다.
- 그 외에는 cat1=C01을 절대 선택하지 않고, A01~A05 또는 B02 중에서만 선택한다.

대분류 목록:
{cat_list}

출력 스키마:
{{"region":"경주","cat1":"A02"}}

중요: 가능하면 시/군 단위를 우선적으로 추출하되, 없으면 시/도 단위로 추출하세요.

요청: {user_query}
""".strip()
            resp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "반드시 유효한 JSON만 출력하세요."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=REGION_EXTRACT_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            region = (data.get("region") or "").strip()
            region = NORMALIZE_REGION.get(region, region)
            cat1 = (data.get("cat1") or "").strip().upper()
            if cat1 not in _VALID_CAT1_CODES:
                cat1 = None
            # 최후 방어: 여전히 C01이면 무효화 (검색단은 관광지 전용)
            if cat1 == COURSE_CAT1_CODE:
                cat1 = None

            if not region:
                text = (user_query or "").strip()
                region = next((w for w in REGION_HINTS if w in text), "")
            print(f"[DEBUG] 추출된 지역: '{region}', 카테고리: '{cat1}', 원본 쿼리: '{user_query}'")
            return region, cat1
        except Exception:
            text = (user_query or "").strip()
            region = next((w for w in REGION_HINTS if w in text), "")
            return region, None

    # --- 1-1) (폴백) TourAPI로 광역 areaCode 해석 ---
    def _resolve_area_code(
        self, region_name: str, tour_api_key: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        if not region_name:
            return None, None
        items = self.tour.area_codes(rows=100, service_key=tour_api_key)
        if not items:
            return None, None
        name = (
            (region_name or "")
            .replace("특별자치도", "").replace("광역시", "").replace("특별시", "").replace("도", "")
            .strip()
        )
        cand = [it for it in items if name and name in (it.get("name") or "")]
        if not cand:
            print(f"[DEBUG] 지역명 '{region_name}' -> 정규화 '{name}' -> 매칭 실패")
            return None, None
        code = cand[0].get("code")
        print(f"[DEBUG] 지역명 '{region_name}' -> 정규화 '{name}' -> 코드 '{code}'")
        return (str(code) if code else None), None

    # --- 2) 상세 정보/요약/이미지 ---
    def _fetch_detail_common(
        self, content_id: str, tour_api_key: Optional[str] = None
    ) -> Tuple[str, str, Optional[float], Optional[float]]:
        item = self.tour.detail_common(content_id, service_key=tour_api_key)
        if not item:
            return "", "", None, None
        overview = (item.get("overview") or "").strip()
        homepage = normalize_homepage(item.get("homepage") or "")
        mx, my = item.get("mapx"), item.get("mapy")
        mapx = float(mx) if mx not in (None, "") else None
        mapy = float(my) if my not in (None, "") else None
        return overview, homepage, mapx, mapy

    def _fetch_detail_image(self, content_id: str, tour_api_key: Optional[str] = None) -> str:
        for item in self.tour.detail_image(content_id, service_key=tour_api_key):
            for key in ("originimgurl", "smallimageurl"):
                valid = validate_image_url(item.get(key) or "")
                if valid:
                    return valid
        return ""

    def _summarize_one_line(self, text: str) -> str:
        source = (text or "").strip()
        if not source:
            return ""
        try:
            resp = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "한국어 문장 하나로만 답해. 금지어: 요약,정리,한줄,한 문장. 28~48자."},
                    {"role": "user", "content":
                        "예시입력: 천지연폭포는 계곡과 숲길이 아름답습니다.\n"
                        "예시출력: 숲길과 어우러진 천지연폭포의 경치를 즐길 수 있습니다.\n\n"
                        f"다음 글을 같은 형식으로 요약:\n{source}"},
                ],
                temperature=0.0,
                max_tokens=SUMMARY_MAX_TOKENS,
            )
            summary = (resp.choices[0].message.content or "").strip()
            summary = re.split(r"[.!?。]\s*", summary)[0].strip()
            return (summary + ".") if summary else ""
        except Exception as exc:
            print(f"요약 생성 실패: {exc}")
            fallback = re.split(r"[.!?。]\s*", source)[0].strip()
            return (fallback[:40] + ("..." if len(fallback) > 40 else "")) if fallback else "관광지 정보를 확인해보세요."

    # --- 3) 목록 정리 휴리스틱(상업매장 제거 등) ---
    def _clean_items(self, items: List[dict]) -> List[dict]:
        ok = []
        for it in items:
            title = (it.get("title") or "").strip()
            if not title:
                continue
            if re.search(r"(대리점|지점|점$|마트|백화점|면세점|아울렛|할인점|스토어)", title):
                continue
            if not it.get("areacode"):
                if re.search(r"(○○점|영업소|직영점|가맹점)", title):
                    continue
            ok.append(it)
        return ok

    # --- 4) 이미지 선택 ---
    def _pick_valid_image(
        self, cid_key: str, firstimage2: str, firstimage: str, tour_api_key: Optional[str] = None
    ) -> str:
        cached = self._img_cache.get(cid_key)
        if cached:
            return cached
        for raw in (firstimage2, firstimage):
            valid = validate_image_url(raw)
            if valid:
                self._img_cache.set(cid_key, valid)
                return valid
        img = self._fetch_detail_image(cid_key, tour_api_key=tour_api_key)
        if img:
            self._img_cache.set(cid_key, img)
        return img

    # --- 메인: 추천 아이템 ---
    def recommend_items(
        self, user_query: str, want: Optional[int] = None, tour_api_key: Optional[str] = None
    ) -> List[TourCard]:
        want = want or NUM_RECOMMEND

        # (1) 지역/대분류
        region, cat1 = self._extract_region_and_cat1(user_query)

        # (1-1) 고속 매핑: 시/군까지 즉시 고정
        area_code, sigungu_code = fast_area_sigungu(region)

        # (1-2) 실패 시 기존 해석 + 키워드 힌트 폴백
        if not area_code:
            ac2, sg2 = self._resolve_area_code(region, tour_api_key=tour_api_key)
            area_code = area_code or ac2
            sigungu_code = sigungu_code or sg2
            if not area_code:
                ac_hint, sg_hint = self._area_hint_from_keyword(user_query)
                area_code = area_code or ac_hint
                sigungu_code = sigungu_code or sg_hint

        # (2) 지역기반 목록(areaBasedList2) + 대표이미지 보장 정렬
        num_rows = max(TOURAPI_LIST_MIN_ROWS, want * API_FETCH_MULTIPLIER)
        print(f"[DEBUG] TourAPI 호출 매개변수: areaCode={area_code}, sigunguCode={sigungu_code}, cat1={cat1}, numOfRows={num_rows}")
        items = self.tour.area_based_list(
            rows=num_rows,
            area_code=area_code,
            sigungu_code=sigungu_code,
            cat1=cat1,  # ※ 여기서 C01은 이미 금지 상태
            service_key=tour_api_key,
        )

        # (2-0) 데이터 레벨 1차 차단: 여행코스(contentTypeId=25) 제거
        def _not_course(it: dict) -> bool:
            ctid = str(it.get("contenttypeid") or it.get("contentTypeId") or "").strip()
            return ctid != COURSE_CONTENT_TYPE_ID

        items = [it for it in items if _not_course(it)]

        # (2-0b) 관광지가 하나도 없으면 화이트리스트 contentTypeId로 재쿼리(12/14/28/32/38/39)
        if not items:
            merged: List[dict] = []
            for ctid in TOURIST_CONTENT_TYPE_WHITELIST:
                merged.extend(self.tour.area_based_list(
                    rows=num_rows,
                    area_code=area_code,
                    sigungu_code=sigungu_code,
                    cat1=cat1,
                    content_type_id=ctid,
                    service_key=tour_api_key,
                ))
            items = merged

        # (2-1) 휴리스틱 정리
        items = self._clean_items(items)

        # (2-2) 최종 방어 필터(타 지역 누출 차단)
        if area_code:
            items = [it for it in items if str(it.get("areacode") or "").strip() == str(area_code)]
        if sigungu_code:
            items = [it for it in items if str(it.get("sigungucode") or it.get("sigunguCode") or "").strip() == str(sigungu_code)]

        # (2-3) 혹시 섞여 들어온 C01(cat1)이 있으면 제거 (이중 안전장치)
        items = [it for it in items if (it.get("cat1") or "").strip().upper() != COURSE_CAT1_CODE]

        if not items:
            return []

        sample = random.sample(items, k=min(want, len(items)))

        out: List[TourCard] = []
        for it in sample:
            cid = (it.get("contentid") or "").strip()
            title = (it.get("title") or "").replace("<b>", "").replace("</b>", "").strip()
            addr = _compose_full_address((it.get("addr1") or ""), (it.get("addr2") or ""))

            overview, homepage, mapx, mapy = self._fetch_detail_common(cid, tour_api_key=tour_api_key)

            reason = self._summarize_one_line(overview) or (
                overview[:120] + "..." if overview else "관광지 정보를 확인해보세요."
            )

            img = self._pick_valid_image(
                cid,
                to_https((it.get("firstimage2") or "")),
                to_https((it.get("firstimage") or "")),
                tour_api_key=tour_api_key,
            )

            map_url = ""
            if mapx is not None and mapy is not None:
                map_url = GOOGLE_MAPS_QUERY_URL_TEMPLATE.format(lat=mapy, lng=mapx)

            metadata: CardMetadata = {
                "contentid": cid,
                "cat1": (it.get("cat1") or ""),
                "addr1": (it.get("addr1") or ""),
                "firstimage2": (it.get("firstimage2") or ""),
                "title": title,
                "region": region,
                "mapx": mapx,
                "mapy": mapy,
                "areacode": it.get("areacode"),
                "sigungucode": it.get("sigungucode") or it.get("sigunguCode"),
                "contenttypeid": it.get("contenttypeid") or it.get("contentTypeId"),
            }
            out.append({
                "name": title or "이름 정보 없음",
                "reason": reason or "한 줄 설명 없음",
                "address": addr or "주소 정보 없음",
                "image_url": img,
                "homepage": homepage,
                "map_url": map_url,
                "metadata": metadata,
            })

        return out[:want]
