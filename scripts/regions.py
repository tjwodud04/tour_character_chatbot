# scripts/regions.py
# 지역/시군 매핑 상수 + 경량 매핑 유틸
# - 입력된 행정명(예: '강원특별자치도', '경주시', '가평군')을 정규화하여
#   (areaCode, sigunguCode)로 빠르게 매핑합니다.
# - sigunguCode는 시/군 단위일 때만 존재하며, 도/광역 단위 입력이면 None입니다.

from __future__ import annotations
from typing import Tuple, Optional

# ──────────────────────────────────────────────────────────────────────────────
# 1) 광역 → areaCode
# ──────────────────────────────────────────────────────────────────────────────
AREA_NAME_TO_CODE = {
    "서울": "1",
    "인천": "2",
    "대전": "3",
    "대구": "4",
    "광주": "5",
    "부산": "6",
    "울산": "7",
    "세종": "8",
    "경기": "31",
    "강원": "32",   # 강원특별자치도 포함
    "충북": "33",
    "충남": "34",
    "경북": "35",
    "경남": "36",
    "전북": "37",   # 전북특별자치도 포함
    "전남": "38",
    "제주": "39",
}

# ──────────────────────────────────────────────────────────────────────────────
# 2) areaCode 별 시·군 → sigunguCode
#    (질문에서 제공된 공식 목록을 그대로 반영)
# ──────────────────────────────────────────────────────────────────────────────
SIGUNGU_BY_AREA = {
    # 서울특별시
    "1": { 
        "강남구": "1", "강동구": "2", "강북구": "3", "강서구": "4", "관악구": "5", "광진구": "6",        "구로구": "7", "금천구": "8", "노원구": "9",       "도봉구": "10","동대문구": "11", "동작구": "12",
        "마포구": "13","서대문구": "14", "서초구": "15",
        "성동구": "16", "성북구": "17", "송파구": "18",
        "양천구": "19", "영등포구": "20", "용산구": "21",
        "은평구": "22", "종로구": "23", "중구": "24",
        "중랑구": "25",
    },
    # 31) 경기도
    "31": {
        "가평": "1", "고양": "2", "과천": "3", "광명": "4", "광주": "5", "구리": "6", "군포": "7",
        "김포": "8", "남양주": "9", "동두천": "10", "부천": "11", "성남": "12", "수원": "13",
        "시흥": "14", "안산": "15", "안성": "16", "안양": "17", "양주": "18", "양평": "19",
        "여주": "20", "연천": "21", "오산": "22", "용인": "23", "의왕": "24", "의정부": "25",
        "이천": "26", "파주": "27", "평택": "28", "포천": "29", "하남": "30", "화성": "31",
    },

    # 32) 강원특별자치도
    "32": {
        "강릉": "1", "고성": "2", "동해": "3", "삼척": "4", "속초": "5", "양구": "6", "양양": "7",
        "영월": "8", "원주": "9", "인제": "10", "정선": "11", "철원": "12", "춘천": "13",
        "태백": "14", "평창": "15", "홍천": "16", "화천": "17", "횡성": "18",
    },

    # 33) 충청북도
    "33": {
        "괴산": "1", "단양": "2", "보은": "3", "영동": "4", "옥천": "5", "음성": "6",
        "제천": "7", "진천": "8", "청원": "9", "청주": "10", "충주": "11", "증평": "12",
    },

    # 34) 충청남도
    "34": {
        "공주": "1", "금산": "2", "논산": "3", "당진": "4", "보령": "5", "부여": "6",
        "서산": "7", "서천": "8", "아산": "9",
        # (제공 목록상 code=10 항목 없음)
        "예산": "11", "천안": "12", "청양": "13", "태안": "14", "홍성": "15", "계룡": "16",
    },

    # 35) 경상북도
    "35": {
        "경산": "1", "경주": "2", "고령": "3", "구미": "4",
        "김천": "6", "문경": "7", "봉화": "8", "상주": "9", "성주": "10",
        "안동": "11", "영덕": "12", "영양": "13", "영주": "14", "영천": "15",
        "예천": "16", "울릉": "17", "울진": "18", "의성": "19",
        "청도": "20", "청송": "21", "칠곡": "22", "포항": "23",
    },

    # 36) 경상남도
    "36": {
        "거제": "1", "거창": "2", "고성": "3", "김해": "4", "남해": "5", "마산": "6", "밀양": "7",
        "사천": "8", "산청": "9", "양산": "10",
        # (제공 목록상 code=11 항목 없음)
        "의령": "12", "진주": "13", "진해": "14", "창녕": "15", "창원": "16", "통영": "17",
        "하동": "18", "함안": "19", "함양": "20", "합천": "21",
    },

    # 37) 전북특별자치도
    "37": {
        "고창": "1", "군산": "2", "김제": "3", "남원": "4", "무주": "5", "부안": "6", "순창": "7",
        "완주": "8", "익산": "9", "임실": "10", "장수": "11", "전주": "12", "정읍": "13", "진안": "14",
    },

    # 38) 전라남도 
    "38": {
        "강진": "1", "고흥": "2", "곡성": "3",
        "광양": "4", "구례": "5", "나주": "6",
        "담양": "7", "목포": "8", "무안": "9",
        "보성": "10", "순천": "11", "신안": "12",
        "여수": "13", "영광": "16", "영암": "17",
        "완도": "18", "장성": "19", "장흥": "20",
        "진도": "21", "함평": "22", "해남": "23",
        "화순": "24",
    },
}

# (선택) 유명 지명 → 구 매핑(결정론 소사전)
SEOUL_POI_ALIAS_TO_GU = {
    "명동": "중구",
    "남산": "중구",     # (상황에 따라 '용산구'도 가능하지만, 명동/남산타워 문의는 중구 의도 빈도↑)
    "남산타워": "중구",
    "N서울타워": "중구",
    "홍대": "마포구",
    "홍대입구": "마포구",
    "연남동": "마포구",
    "합정": "마포구",
    "강남역": "강남구",
    "가로수길": "강남구",
    "코엑스": "강남구",
    "남대문시장": "중구",
    "동대문": "동대문구",
    "DDP": "중구",
    "이태원": "용산구",
}

# ──────────────────────────────────────────────────────────────────────────────
# 3) 정규화 & 빠른 매핑 유틸
# ──────────────────────────────────────────────────────────────────────────────

def strip_suffix(name: str) -> str:
    """
    행정 접미사 제거 → 핵심 토큰만 남김
    - '강원특별자치도' → '강원'
    - '경주시' → '경주'
    - '가평군' → '가평'
    """
    if not name:
        return ""
    x = name
    # 긴 접미사 먼저 제거
    for suf in ("특별자치시", "특별자치도", "광역시", "특별시", "자치시", "자치도"):
        x = x.replace(suf, "")
    # 짧은 접미사 제거
    for suf in ("시", "군", "도"):
        if x.endswith(suf):
            x = x[: -len(suf)]
    return x.strip()


def fast_area_sigungu(name: Optional[str],
                      prefer_area: Optional[str] = None
                     ) -> Tuple[Optional[str], Optional[str]]:
    """
    입력된 지역명을 정규화 후 (areaCode, sigunguCode)로 매핑.
    - name: '경주', '가평군', '경기도', '서울 중구', '홍대' 등
    - prefer_area: 모호 지명(예: '고성') 분해석 힌트. '강원'/'경남' 또는 '32'/'36' 등.
      제공 시 해당 광역의 시군 테이블을 우선 탐색합니다.

    반환:
      (areaCode, sigunguCode)
      - 광역 단위 입력 시: (areaCode, None)
      - 시군 단위 입력 시: (areaCode, sigunguCode)
      - 매칭 실패 시: (None, None)
    """
    if not name:
        return None, None

    # 0) 힌트 정규화 → 내부 키로
    prefer_area_key: Optional[str] = None
    if prefer_area:
        p = strip_suffix(prefer_area)
        # '경기'같은 명칭 → 코드, 혹은 이미 코드라면 그대로
        prefer_area_key = AREA_NAME_TO_CODE.get(p, p if p in SIGUNGU_BY_AREA else None)

    # 1) 입력 정규화
    raw = name.strip()
    n = strip_suffix(raw)

    # 2) "서울 중구" 같은 복합 표기 우선 처리
    #   - 문장 내에 광역이 보이면 해당 광역의 시군 테이블에서 구/시 매칭 시도
    for area_name, acode in AREA_NAME_TO_CODE.items():
        if area_name in n:
            # 광역명 제거하고 남은 토큰들을 시군구로 간주하여 탐색
            rest = n.replace(area_name, "").strip()
            if rest:
                table = SIGUNGU_BY_AREA.get(acode, {})
                # 정확 일치
                if rest in table:
                    return acode, table[rest]
                # 부분 포함(예: '중구 쇼핑' → '중구')
                for sgg_name, sgg_code in table.items():
                    if sgg_name in rest:
                        return acode, sgg_code
            # 구가 없으면 광역만 확정
            return acode, None

    # 3) 광역 직접 매칭 (예: '경기도', '강원특별자치도')
    if n in AREA_NAME_TO_CODE:
        return AREA_NAME_TO_CODE[n], None

    # 4) (옵션) prefer_area 힌트가 있으면 해당 광역 먼저 탐색
    if prefer_area_key and prefer_area_key in SIGUNGU_BY_AREA:
        table = SIGUNGU_BY_AREA[prefer_area_key]
        # 정확 일치
        if n in table:
            return prefer_area_key, table[n]
        # 부분 포함 보조
        for sgg_name, sgg_code in table.items():
            if sgg_name in n:
                return prefer_area_key, sgg_code

    # 5) 모든 광역의 시군 테이블에서 탐색 (정확 일치 → 부분 포함 순)
    for area_code, table in SIGUNGU_BY_AREA.items():
        if n in table:
            return area_code, table[n]
    for area_code, table in SIGUNGU_BY_AREA.items():
        for sgg_name, sgg_code in table.items():
            if sgg_name in n:
                return area_code, sgg_code

    # 6) 서울 POI alias → 구 매핑 (명동/홍대/남산 등)
    sg_map_seoul = SIGUNGU_BY_AREA.get("1", {})
    gu_alias = SEOUL_POI_ALIAS_TO_GU.get(n)
    if not gu_alias:
        # 부분 포함 alias(예: '명동 쇼핑')
        for k, v in SEOUL_POI_ALIAS_TO_GU.items():
            if k in n:
                gu_alias = v
                break
    if gu_alias:
        sgg_code = sg_map_seoul.get(gu_alias)
        if sgg_code:
            return "1", sgg_code

    # 7) 실패
    return None, None

# ──────────────────────────────────────────────────────────────────────────────
# 4) 편의: areaCode로 다시 광역/시군명을 얻고 싶을 때 (선택 사용)
# ──────────────────────────────────────────────────────────────────────────────

def area_name_from_code(area_code: str) -> Optional[str]:
    """'31' → '경기' 등 역매핑 (여러 키 중 첫 매칭 반환)"""
    if not area_code:
        return None
    for name, code in AREA_NAME_TO_CODE.items():
        if str(code) == str(area_code):
            return name
    return None


def sigungu_name_from_code(area_code: str, sigungu_code: str) -> Optional[str]:
    """('31','1') → '가평' 등 역매핑"""
    if not area_code or not sigungu_code:
        return None
    table = SIGUNGU_BY_AREA.get(str(area_code))
    if not table:
        return None
    for name, code in table.items():
        if str(code) == str(sigungu_code):
            return name
    return None
