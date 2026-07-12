"""이미지/홈페이지 URL 정규화·검증 유틸과 TTL 캐시.

TourAPI가 돌려주는 대표 이미지 URL을 https로 승격하고, 확장자/도메인/HEAD 응답을
검사해 신뢰할 수 있는 것만 통과시킨다. 검증 결과는 콘텐츠 ID 기준으로 캐시한다.
"""

from __future__ import annotations

import re
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from scripts.config import (
    IMAGE_ALLOWED_EXTS,
    IMAGE_DENY_DOMAINS,
    IMAGE_HEAD_TIMEOUT,
    IMAGE_HEAD_WHITELIST_NOHEAD,
    IMAGE_MAX_BYTES,
    IMAGE_MIN_BYTES,
    IMAGE_REQUIRE_HEAD_OK,
)


def to_https(url: str) -> str:
    """`http://` URL을 `https://`로 승격한다."""
    url = (url or "").strip()
    if not url:
        return ""
    return "https://" + url[len("http://"):] if url.startswith("http://") else url


def has_allowed_ext(url: str) -> bool:
    """URL 경로의 확장자가 허용 이미지 확장자인지 확인한다."""
    path = urlparse(url).path.lower()
    return "." in path and path.rsplit(".", 1)[-1] in IMAGE_ALLOWED_EXTS


def is_domain_blocked(url: str) -> bool:
    """차단 도메인(또는 그 서브도메인)인지 확인한다."""
    host = urlparse(url).netloc.lower().split(":")[0]
    return any(host == d or host.endswith("." + d) for d in IMAGE_DENY_DOMAINS)


def head_ok(url: str) -> bool:
    """HEAD 요청으로 이미지 응답(타입/크기)이 정상인지 확인한다."""
    if not IMAGE_REQUIRE_HEAD_OK:
        return True
    host = urlparse(url).netloc.lower().split(":")[0]
    if host in IMAGE_HEAD_WHITELIST_NOHEAD:
        return True
    try:
        resp = requests.head(url, allow_redirects=True, timeout=IMAGE_HEAD_TIMEOUT)
        if resp.status_code >= 400:
            return False
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if not ctype.startswith("image/"):
            return False
        clen = resp.headers.get("Content-Length")
        if clen and clen.isdigit():
            size = int(clen)
            if size < IMAGE_MIN_BYTES or size > IMAGE_MAX_BYTES:
                return False
        return True
    except Exception:
        return False


def validate_image_url(url: str) -> str:
    """검증을 통과한 https 이미지 URL을 반환하고, 실패 시 빈 문자열을 반환한다."""
    url = to_https(url)
    if not url or is_domain_blocked(url) or not has_allowed_ext(url) or not head_ok(url):
        return ""
    return url


def normalize_homepage(raw: str) -> str:
    """TourAPI homepage 필드(HTML 앵커 등 포함)를 순수 https URL로 정규화한다."""
    text = (raw or "").strip()
    if not text:
        return ""
    match = re.search(r'href=["\']([^"\']+)["\']', text, re.I)
    if match:
        text = match.group(1).strip()
    text = text.replace("&amp;", "&")
    if text.startswith("//"):
        text = "https:" + text
    if not re.match(r"^https?://", text, re.I):
        text = "https://" + text
    return to_https(text)


class ImageCache:
    """콘텐츠 ID → 검증된 이미지 URL 매핑을 담는 TTL·용량 제한 캐시."""

    def __init__(self, ttl_sec: int, max_size: int):
        self.ttl = ttl_sec
        self.max = max_size
        self.store: Dict[str, Tuple[str, float]] = {}

    def _expired(self, ts: float) -> bool:
        return (time.time() - ts) > self.ttl if self.ttl > 0 else False

    def get(self, key: Optional[str]) -> str:
        if not key:
            return ""
        entry = self.store.get(key)
        if not entry:
            return ""
        url, ts = entry
        if self._expired(ts):
            self.store.pop(key, None)
            return ""
        return url

    def set(self, key: Optional[str], url: str) -> None:
        if not key or not url:
            return
        # 용량 초과 시 오래된 절반을 제거(단순 LRU 근사)
        if self.max > 0 and len(self.store) >= self.max:
            oldest = sorted(self.store.items(), key=lambda kv: kv[1][1])[: max(1, self.max // 2)]
            for old_key, _ in oldest:
                self.store.pop(old_key, None)
        self.store[key] = (url, time.time())
