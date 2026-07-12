"""채팅/스트리밍 핸들러와 코스 조회 등 요청 처리 비즈니스 로직.

`process_chat`(한 번에 응답)과 `stream_chat`(SSE)은 오디오 → STT → 관광지 검색 →
답변 문구 생성까지 동일한 파이프라인을 공유하며, 이 부분을 `_prepare_chat`로 추출했다.
SSE 이벤트 형식과 JSON 응답 키(= 프런트엔드 계약)는 그대로 유지한다.
"""

import asyncio
import base64
import datetime
import json
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from flask import Response, abort, jsonify, stream_with_context
from openai import AsyncOpenAI

from scripts.config import (
    BLOB_HTTP_TIMEOUT,
    CHARACTER_VOICE,
    COURSE_INDEX_BLOB_FILENAME,
    COURSE_RECOMMEND_COUNT,
    DEFAULT_CHARACTER,
    HISTORY_MAX_LEN,
    NO_RESULT_REPLY,
    NUM_RECOMMEND,
    OPENAI_STT_MODEL,
    OPENAI_TTS_MODEL,
    VERCEL_BLOB_API_URL,
    VERCEL_BLOB_PUBLIC_BASE,
    VERCEL_PROJ_ID,
    VERCEL_TOKEN,
)
from scripts.schemas import CourseCard, TourCard
from scripts.search_service import SearchService
from scripts.utils import copula_iy_a, remove_emojis, remove_empty_parentheses

# ======================================================================================
# 글로벌 상태
# ======================================================================================
conversation_history: List[Dict[str, Any]] = []
history_lock = threading.Lock()


# ======================================================================================
# 공통 I/O
# ======================================================================================
def get_openai_client(api_key: str) -> AsyncOpenAI:
    """API 키를 검증하고 비동기 OpenAI 클라이언트를 생성한다."""
    if not api_key:
        abort(401, description="OpenAI API 키가 필요합니다.")
    return AsyncOpenAI(api_key=api_key)


def upload_log_to_vercel_blob(blob_name: str, data: dict) -> None:
    """대화 로그를 Vercel Blob에 업로드한다(ENV 미설정 시 조용히 생략)."""
    if not VERCEL_TOKEN or not VERCEL_PROJ_ID:
        print("[log] Vercel ENV 미설정: 로그 업로드 생략")
        return
    try:
        b64_data = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
        resp = requests.post(
            VERCEL_BLOB_API_URL,
            headers={"Authorization": f"Bearer {VERCEL_TOKEN}"},
            json={"projectId": VERCEL_PROJ_ID, "data": b64_data, "name": blob_name},
        )
        resp.raise_for_status()
        print(f"로그 저장 성공: {blob_name}")
    except Exception as exc:
        print(f"Vercel Blob 로그 업로드 예외: {exc}")


# ======================================================================================
# 유틸: 첫 답변 프리픽스 & 코스 로딩
# ======================================================================================
def _first_reply_prefix(recs: List[TourCard], character: str = DEFAULT_CHARACTER) -> str:
    """관광지는 괄호 없이 콤마로 나열하고, 캐릭터별 톤을 달리해 첫 답변 문구를 구성."""
    if not recs:
        return ""
    names = [(r.get("name") or "").strip() for r in recs if r.get("name")]
    names = [n for n in names if n][:3]
    names_str = ", ".join(names) if names else "관광지"
    # 마지막 명사를 기준으로 '이야/야' 선택
    last_name = names[-1] if names else "관광지"
    cop = copula_iy_a(last_name)

    if character == "kei":
        # Kei 전용 문구
        return (
            f"추천하는 관광지는 {names_str}{cop}! "
            f"더 자세한 내용은 아래의 카드를 참고해 줘. "
            f"추가로, 추천 관광 코스도 보여줄 수 있는데, 원해?"
        )
    # Haru 등은 기존 톤 유지(간결)
    return (
        f"관광지 {names_str}{cop} 추천입니다. "
        f"자세한 내용은 아래 카드를 참고해 주세요. "
        f"원하시면 관련 관광 코스도 제안해 드릴까요?"
    )


def _download_blob_json_by_name(blob_filename: str) -> List[dict]:
    """Vercel Blob 퍼블릭 베이스에서 JSON 파일을 받아 리스트로 반환한다."""
    base = (VERCEL_BLOB_PUBLIC_BASE or "").rstrip("/")
    if not base:
        return []
    url = f"{base}/{blob_filename.lstrip('/')}"
    try:
        resp = requests.get(url, timeout=BLOB_HTTP_TIMEOUT)
        resp.raise_for_status()
        ctype = (resp.headers.get("Content-Type") or "").lower()
        data = resp.json() if "json" in ctype else json.loads(resp.text or "[]")
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"[Blob] 코스 인덱스 로드 실패: {exc}")
        return []


def pick_courses_for_region(region: str, n: int = COURSE_RECOMMEND_COUNT) -> List[CourseCard]:
    """코스 인덱스에서 지역이 일치하는 코스 카드를 최대 n개 고른다."""
    raw = _download_blob_json_by_name(COURSE_INDEX_BLOB_FILENAME)
    if not raw:
        return []

    def _norm_region(s: str) -> str:
        s = (s or "").strip()
        return s.replace("특별자치도", "").replace("광역시", "").replace("특별시", "").replace("도", "").strip()

    def _get(d: dict, keys: List[str], default: str = "") -> str:
        for k in keys:
            if d.get(k):
                return d[k]
        return default

    want = _norm_region(region)
    picked: List[CourseCard] = []
    for it in raw:
        loc = _get(it, ["location", "지역", "시도", "area"], "")
        locn = _norm_region(str(loc))
        if not want or (want in locn) or (locn in want):
            title = _get(it, ["title", "name", "코스명", "제목"], "코스")
            thumb = _get(it, ["thumbnail", "thumb", "image", "이미지"], "")
            link = _get(it, ["course_url", "url", "link", "href"], "")
            spots = it.get("spots") if isinstance(it.get("spots"), list) else []
            desc = " · ".join([str(s) for s in spots[:3]]) if spots else ""
            picked.append({"title": str(title), "thumbnail": str(thumb), "link": str(link), "desc": str(desc)})
            if len(picked) >= n:
                break
    return picked


# ======================================================================================
# 공통 파이프라인: 오디오 → STT → 검색 → 답변 문구
# ======================================================================================
@dataclass
class _ChatPrep:
    client: AsyncOpenAI
    character: str
    user_text: str
    recs: List[TourCard]
    reply_text: str


def _request_context(req) -> tuple[str, Optional[str], str]:
    """요청 헤더/폼에서 OpenAI 키·TourAPI 키·캐릭터를 추출한다."""
    api_key = (req.headers.get("X-API-KEY") or "").strip()
    tour_api_key = req.headers.get("X-TOUR-API-KEY")
    character = req.form.get("character", DEFAULT_CHARACTER)
    return api_key, tour_api_key, character


def _compose_reply(recs: List[TourCard], character: str) -> str:
    """추천 결과로 답변 문구를 만들고 빈 괄호/이모지를 제거한다."""
    text = _first_reply_prefix(recs, character) if recs else NO_RESULT_REPLY
    return remove_empty_parentheses(remove_emojis(text))


async def _prepare_chat(req) -> _ChatPrep:
    """오디오 → STT → 관광지 검색 → 답변 문구까지의 공통 처리."""
    api_key, tour_api_key, character = _request_context(req)
    client = get_openai_client(api_key)

    audio_file = req.files["audio"]
    stt_result = await client.audio.transcriptions.create(
        file=("audio.webm", audio_file.read()),
        model=OPENAI_STT_MODEL,
        response_format="text",
    )
    user_text = stt_result or ""

    recs = SearchService(openai_api_key=api_key).search(
        user_text, top_k=NUM_RECOMMEND, tour_api_key=tour_api_key, openai_api_key=api_key
    )
    reply_text = _compose_reply(recs, character)
    return _ChatPrep(client=client, character=character, user_text=user_text, recs=recs, reply_text=reply_text)


# ======================================================================================
# 메인 처리(한 번에)
# ======================================================================================
async def process_chat(req):
    if "audio" not in req.files:
        return jsonify(error="오디오 파일이 필요합니다."), 400

    try:
        prep = await _prepare_chat(req)

        # TTS
        audio_response = await prep.client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=CHARACTER_VOICE[prep.character],
            input=prep.reply_text,
        )
        audio_b64 = base64.b64encode(audio_response.content).decode()

        # 히스토리
        now_kst_iso = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        with history_lock:
            conversation_history.append({"role": "user", "content": prep.user_text, "ts": now_kst_iso})
            conversation_history.append({"role": "assistant", "content": prep.reply_text, "ts": now_kst_iso})
            if len(conversation_history) > HISTORY_MAX_LEN:
                conversation_history[:] = conversation_history[-HISTORY_MAX_LEN:]

        # 로그(fire-and-forget)
        now = datetime.datetime.now(datetime.timezone.utc)
        blob_name = f"logs/{now.strftime('%Y-%m-%dT%H-%M-%SZ')}_{prep.character}.json"
        log_data = {
            "timestamp": now_kst_iso,
            "character": prep.character,
            "user_text": prep.user_text,
            "ai_text": prep.reply_text,
            "recommendations": prep.recs,
        }
        asyncio.create_task(asyncio.to_thread(upload_log_to_vercel_blob, blob_name, log_data))

        return jsonify({
            "user_text": prep.user_text,
            "ai_text": prep.reply_text,
            "audio": audio_b64,
            "tour_recommendations": prep.recs,
        })

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to process request: {exc}"}), 500


# ======================================================================================
# 스트리밍 처리
# ======================================================================================
async def stream_chat(req):
    if "audio" not in req.files:
        return jsonify(error="오디오 파일이 필요합니다."), 400

    prep = await _prepare_chat(req)
    client, character, final_text, recs = prep.client, prep.character, prep.reply_text, prep.recs

    # 지역/카테고리 힌트
    region_hint = (recs[0].get("metadata") or {}).get("region") if recs else ""
    cat1_hint = (recs[0].get("metadata") or {}).get("cat1") if recs else ""

    async def event_stream():
        # 1) 메타: region/cat1 힌트
        yield f"event: meta\ndata: {json.dumps({'region': region_hint or '', 'cat1': cat1_hint or ''}, ensure_ascii=False)}\n\n"
        # 2) 프리픽스 토큰: 완성 텍스트를 한 번에 흘려 UI 스켈레톤 채움
        newlines = "\n\n"
        yield f"event: token\ndata: {json.dumps({'token': final_text + newlines}, ensure_ascii=False)}\n\n"

        # 3) TTS: gpt-4o-mini-tts로 음성 생성 (실패 시 무음)
        audio_b64 = ""
        try:
            audio_response = await client.audio.speech.create(
                model=OPENAI_TTS_MODEL,
                voice=CHARACTER_VOICE[character],
                input=final_text,
            )
            audio_b64 = base64.b64encode(audio_response.content).decode()
        except Exception:
            pass

        payload = {"ai_text": final_text, "audio": audio_b64, "tour_recommendations": recs}
        yield f"event: final\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
