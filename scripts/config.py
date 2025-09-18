import os

VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_PROJ_ID = os.getenv("VERCEL_PROJECT_ID")

# TourAPI 설정
KOREA_TOURISM_API_BASE = "http://apis.data.go.kr/B551011/KorService2"
KOREA_TOURISM_API_KEY = os.getenv("KOREA_TOURISM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# 관광지 추천 설정
NUM_RECOMMEND = 5
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

# 임베딩 캐시 설정
VECTOR_CACHE_PATH = os.getenv("VECTOR_CACHE_PATH", "vector_cache.jsonl")
CACHE_SIM_THRESHOLD = 0.82
MAX_CACHE_ITEMS = 500

CHARACTER_SYSTEM_PROMPTS = {
    "kei": "당신은 친근하고 창의적인 한국 관광 가이드입니다. 사용자의 여행 취향과 관심사를 파악해서 적절한 관광지를 추천해주세요. 따뜻하고 친근한 톤으로 관광지의 매력을 설명해주세요.",
    "haru": "당신은 전문적이고 체계적인 여행 컨설턴트입니다. 사용자의 요구사항을 정확히 분석해서 최적의 관광지를 추천해주세요. 명확하고 실용적인 정보를 제공하며 전문성 있게 안내해주세요."
}

CHARACTER_VOICE = {
    "kei": "alloy",
    "haru": "shimmer"
}

HISTORY_MAX_LEN = 10 