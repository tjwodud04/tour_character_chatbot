import os

VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_PROJ_ID = os.getenv("VERCEL_PROJECT_ID")

# 읽기 전용 퍼블릭 베이스 URL (예: https://xxxx.public.blob.vercel-storage.com)
VERCEL_BLOB_PUBLIC_BASE = os.getenv(
    "VERCEL_BLOB_PUBLIC_BASE",
    "https://hohz7fp3rniqdmon.public.blob.vercel-storage.com"
)
# (선택) RW 토큰이 있을 때만 Vercel API 목록 조회 폴백 사용
VERCEL_BLOB_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv("VERCEL_BLOB_TOKEN")

# 코스 인덱스 파일명/개수
COURSE_INDEX_BLOB_FILENAME = os.getenv("COURSE_INDEX_BLOB_FILENAME", "web_courses_index_selenium.json")
COURSE_RECOMMEND_COUNT = int(os.getenv("COURSE_RECOMMEND_COUNT", "3"))
COURSE_INDEX_FULL_URL = os.getenv(
    "COURSE_INDEX_FULL_URL",
    "https://hohz7fp3rniqdmon.public.blob.vercel-storage.com/web_courses_index_selenium.json"
)

# TourAPI 설정
KOREA_TOURISM_API_BASE = "http://apis.data.go.kr/B551011/KorService2"
KOREA_TOURISM_API_KEY = os.getenv("KOREA_TOURISM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# 관광지 추천 설정
NUM_RECOMMEND = 3
API_FETCH_MULTIPLIER = 6
TIMEOUT = 10

# 이미지 검증 설정
IMAGE_CACHE_TTL_SEC = 7 * 24 * 3600
IMAGE_CACHE_MAX = 1000
IMAGE_MIN_BYTES = 1024
IMAGE_MAX_BYTES = 15 * 1024 * 1024
IMAGE_ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}
IMAGE_DENY_DOMAINS = {"example.com", "localhost", "127.0.0.1"}
IMAGE_REQUIRE_HEAD_OK = True
IMAGE_HEAD_WHITELIST_NOHEAD = {"tong.visitkorea.or.kr"}

# 임베딩 캐시 설정 (Redis)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_SIM_THRESHOLD = 0.82
MAX_CACHE_ITEMS = 500
CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7일

CHARACTER_SYSTEM_PROMPTS = {
    "kei": "당신은 친근하고 창의적인 한국 관광 가이드입니다. 사용자의 여행 취향과 관심사를 파악해서 적절한 관광지를 추천해주세요. 따뜻하고 친근한 톤으로 관광지의 매력을 설명해주세요.",
    "haru": "당신은 전문적이고 체계적인 여행 컨설턴트입니다. 사용자의 요구사항을 정확히 분석해서 최적의 관광지를 추천해주세요. 명확하고 실용적인 정보를 제공하며 전문성 있게 안내해주세요."
}

CHARACTER_VOICE = {
    "kei": "alloy",
    "haru": "shimmer"
}

HISTORY_MAX_LEN = 10
CACHE_VERSION = "v10"
