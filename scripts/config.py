"""애플리케이션 전역 설정.

비밀 값(API 키/토큰)은 항상 환경 변수(`os.getenv`)로만 읽고, 그 외 동작을
바꾸는 상수(모델명, 엔드포인트, 지역/이미지 정책, 매직 넘버 등)는 이 모듈에
모아 두어 하드코딩을 제거한다. 다른 모듈은 필요한 이름만 명시적으로 임포트한다.
"""

import os

# ──────────────────────────────────────────────────────────────────────────────
# 비밀 값 (환경 변수에서만 로드)
# ──────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KOREA_TOURISM_API_KEY = os.getenv("KOREA_TOURISM_API_KEY")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_PROJ_ID = os.getenv("VERCEL_PROJECT_ID")
# (선택) RW 토큰이 있을 때만 Vercel API 목록 조회 폴백 사용
VERCEL_BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv("VERCEL_BLOB_TOKEN")

# ──────────────────────────────────────────────────────────────────────────────
# OpenAI 모델 / 음성
# ──────────────────────────────────────────────────────────────────────────────
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")                  # 텍스트(추론) 모델
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_STT_MODEL = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")  # 음성 인식(STT)
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")         # 음성 합성(TTS)
DEFAULT_TTS_VOICE = "alloy"     # CHARACTER_VOICE에 없는 캐릭터의 폴백 음성

# LLM 호출 시 최대 토큰(하드코딩 제거용 상수)
REGION_EXTRACT_MAX_TOKENS = 120   # (region, cat1) 추출
SUMMARY_MAX_TOKENS = 80           # 한 줄 요약

# ──────────────────────────────────────────────────────────────────────────────
# Vercel Blob (로그 업로드 / 코스 인덱스)
# ──────────────────────────────────────────────────────────────────────────────
# 읽기 전용 퍼블릭 베이스 URL (예: https://xxxx.public.blob.vercel-storage.com)
VERCEL_BLOB_PUBLIC_BASE = os.getenv(
    "VERCEL_BLOB_PUBLIC_BASE",
    "https://hohz7fp3rniqdmon.public.blob.vercel-storage.com",
)
VERCEL_BLOB_API_URL = "https://api.vercel.com/v2/blob"   # 로그 업로드 엔드포인트

# 코스 인덱스 파일명/개수/전체 URL
COURSE_INDEX_BLOB_FILENAME = os.getenv("COURSE_INDEX_BLOB_FILENAME", "web_courses_index_selenium.json")
COURSE_RECOMMEND_COUNT = int(os.getenv("COURSE_RECOMMEND_COUNT", "3"))
COURSE_INDEX_FULL_URL = os.getenv(
    "COURSE_INDEX_FULL_URL",
    "https://hohz7fp3rniqdmon.public.blob.vercel-storage.com/web_courses_index_selenium.json",
)

# ──────────────────────────────────────────────────────────────────────────────
# 한국관광공사 TourAPI
# ──────────────────────────────────────────────────────────────────────────────
KOREA_TOURISM_API_BASE = "http://apis.data.go.kr/B551011/KorService2"

# 모든 TourAPI 요청에 공통으로 들어가는 파라미터
TOURAPI_MOBILE_OS = "ETC"
TOURAPI_MOBILE_APP = "TourAPI"
TOURAPI_RESPONSE_TYPE = "json"          # _type
TOURAPI_TIMEOUT = 10                    # 초 (구 TIMEOUT)
TIMEOUT = TOURAPI_TIMEOUT               # 하위 호환 별칭

# areaBasedList2 정렬 코드(O/Q/R: 대표이미지 보장), 목록 최소 조회 수
TOURAPI_ARRANGE_IMAGE_FIRST = "O"
TOURAPI_LIST_MIN_ROWS = 80

# 콘텐츠 타입: 25=여행코스(관광지 검색단에서 차단), 관광지 화이트리스트
COURSE_CONTENT_TYPE_ID = "25"
COURSE_CAT1_CODE = "C01"                # 추천코스 대분류(관광지 검색단에서 차단)
TOURIST_CONTENT_TYPE_WHITELIST = ["12", "14", "28", "32", "38", "39"]

# 관광지 대분류(cat1) 선택지 — LLM 프롬프트 구성 및 유효성 검증에 사용
CAT1_CHOICES = [
    {"code": "A01", "name": "자연"},
    {"code": "A02", "name": "인문(문화/예술/역사)"},
    {"code": "A03", "name": "레포츠"},
    {"code": "A04", "name": "쇼핑"},
    {"code": "A05", "name": "음식"},
    {"code": "B02", "name": "숙박"},
    {"code": "C01", "name": "추천코스"},
]

# 좌표 → 지도 링크 템플릿
GOOGLE_MAPS_QUERY_URL_TEMPLATE = "https://maps.google.com/?q={lat},{lng}"

# ──────────────────────────────────────────────────────────────────────────────
# 관광지 추천 설정
# ──────────────────────────────────────────────────────────────────────────────
NUM_RECOMMEND = 3           # 기본 추천 개수(top-k)
API_FETCH_MULTIPLIER = 6    # 후보 확보용 목록 조회 배수

# ──────────────────────────────────────────────────────────────────────────────
# 이미지 검증 설정
# ──────────────────────────────────────────────────────────────────────────────
IMAGE_CACHE_TTL_SEC = 7 * 24 * 3600
IMAGE_CACHE_MAX = 1000
IMAGE_MIN_BYTES = 1024
IMAGE_MAX_BYTES = 15 * 1024 * 1024
IMAGE_ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}
IMAGE_DENY_DOMAINS = {"example.com", "localhost", "127.0.0.1"}
IMAGE_REQUIRE_HEAD_OK = True
IMAGE_HEAD_WHITELIST_NOHEAD = {"tong.visitkorea.or.kr"}
IMAGE_HEAD_TIMEOUT = 5      # 이미지 HEAD 검증 타임아웃(초)

# 외부 JSON(코스 인덱스 등) 다운로드 타임아웃(초)
BLOB_HTTP_TIMEOUT = 12

# ──────────────────────────────────────────────────────────────────────────────
# 캐릭터별 톤/음성 및 대화 문구
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_CHARACTER = "kei"

CHARACTER_SYSTEM_PROMPTS = {
    "kei": "당신은 친근하고 창의적인 한국 관광 가이드입니다. 사용자의 여행 취향과 관심사를 파악해서 적절한 관광지를 추천해주세요. 따뜻하고 친근한 톤으로 관광지의 매력을 설명해주세요.",
    "haru": "당신은 전문적이고 체계적인 여행 컨설턴트입니다. 사용자의 요구사항을 정확히 분석해서 최적의 관광지를 추천해주세요. 명확하고 실용적인 정보를 제공하며 전문성 있게 안내해주세요.",
}

CHARACTER_VOICE = {
    "kei": "alloy",
    "haru": "shimmer",
}

# 관광지를 찾지 못했을 때의 답변
NO_RESULT_REPLY = "관련 관광지를 아직 찾지 못했어. 지역이나 키워드를 한 번만 더 알려줄래?"
# /scripts/courses 응답에 함께 내려주는 안내 멘트
COURSE_READY_MESSAGE = "원하는 대로 추천 관광 코스 정보를 가져왔어. 아래 카드에서 자세한 내용을 확인해 봐!"

HISTORY_MAX_LEN = 10
CACHE_VERSION = "v11"

# 개발 서버 기본 포트
DEV_SERVER_PORT = int(os.getenv("PORT", "8001"))
