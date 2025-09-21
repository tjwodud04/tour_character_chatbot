import base64
import asyncio
import threading
import json
import requests
import datetime
from typing import Dict, Any, List
from urllib.parse import quote

from flask import jsonify, abort, request, Response, stream_with_context
from openai import AsyncOpenAI

from scripts.config import (
    VERCEL_TOKEN, VERCEL_PROJ_ID,
    CHARACTER_SYSTEM_PROMPTS, CHARACTER_VOICE, HISTORY_MAX_LEN,
    # ▼▼▼ 추가 import ▼▼▼
    VERCEL_BLOB_PUBLIC_BASE, VERCEL_BLOB_TOKEN,
    COURSE_INDEX_BLOB_FILENAME, COURSE_RECOMMEND_COUNT
)
from scripts.utils import remove_empty_parentheses, remove_emojis
from scripts.search_service import SearchService

# ======================================================================================
# 글로벌 상태
# ======================================================================================
conversation_history: List[Dict[str, Any]] = []
history_lock = threading.Lock()

# ======================================================================================
# 공통 I/O
# ======================================================================================
def get_openai_client(api_key: str):
    if not api_key:
        abort(401, description="OpenAI API 키가 필요합니다.")
    return AsyncOpenAI(api_key=api_key)

def upload_log_to_vercel_blob(blob_name: str, data: dict):
    if not VERCEL_TOKEN or not VERCEL_PROJ_ID:
        print("Vercel 환경변수(VERCEL_TOKEN, VERCEL_PROJECT_ID)가 없어 로그를 저장하지 않습니다.")
        return
    try:
        b64_data = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
        resp = requests.post(
            "https://api.vercel.com/v2/blob",
            headers={"Authorization": f"Bearer {VERCEL_TOKEN}"},
            json={"projectId": VERCEL_PROJ_ID, "data": b64_data, "name": blob_name}
        )
        resp.raise_for_status()
        print(f"로그 저장 성공: {blob_name}")
    except Exception as e:
        print(f"Vercel Blob 로그 업로드 예외: {e}")

# ======================================================================================
# 유틸: 첫 답변 머리말 & 지역 코스(Blob)
# ======================================================================================
def _first_reply_prefix(recs: list[dict]) -> str:
    """
    요구사항:
    - 관광지명은 괄호 없이 콤마로만 나열
    - 장문의 부연설명 없이 짧게
    예시: '제주 관광지 따라비 오름, 각시바위오름, 법환포구를 추천해요. 조금 더 자세한 내용은 아래의 카드를 참고해주세요.
          원하시면 지역과 관련된 관광 코스도 추천해줄 수 있는데, 보여드릴까요?'
    """
    if not recs:
        return ""
    names = [ (r.get("name") or "").strip() for r in recs if r.get("name") ]
    names = [n for n in names if n][:3]
    region = (recs[0].get("metadata") or {}).get("region") or ""
    region_part = f"{region} " if region else ""
    names_str = ", ".join(names) if names else "관광지"
    return (
        f"{region_part}관광지 {names_str}를 추천해요. "
        f"조금 더 자세한 내용은 아래의 카드를 참고해주세요.\n\n"
        f"원하시면 지역과 관련된 관광 코스도 추천해줄 수 있는데, 보여드릴까요?"
    )

def _region_key(s: str) -> str:
    if not s: return ""
    return s.replace("특별자치도","").replace("광역시","").replace("특별시","").strip()

def _download_blob_json_by_name(blob_filename: str) -> list[dict]:
    """
    1순위: 퍼블릭 베이스 URL에서 파일 직접 GET
    2순위: (옵션) RW 토큰 있으면 Vercel Blob API 목록 조회 → downloadUrl
    """
    # ----- 1) Public Base 직독 -----
    base = (VERCEL_BLOB_PUBLIC_BASE or "").rstrip("/")
    if base:
        try:
            public_url = f"{base}/{blob_filename.lstrip('/')}"
            r = requests.get(public_url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[Blob] public fetch 실패: {e}")

    # ----- 2) API 목록 폴백 (토큰 필요) -----
    if not VERCEL_BLOB_TOKEN:
        return []
    try:
        list_url = f"https://api.vercel.com/v2/blobs?prefix={quote(blob_filename)}&limit=10"
        r = requests.get(list_url, headers={"Authorization": f"Bearer {VERCEL_BLOB_TOKEN}"}, timeout=10)
        r.raise_for_status()
        items = (r.json().get("blobs") or [])
        match = next((it for it in items if it.get("pathname") == blob_filename or it.get("name") == blob_filename), None)
        if not match:
            match = items[0] if items else None
        if not match:
            return []
        download_url = match.get("downloadUrl") or match.get("url")
        if not download_url:
            return []
        r2 = requests.get(download_url, timeout=15)
        r2.raise_for_status()
        return r2.json()
    except Exception as e:
        print(f"[Blob] 코스 인덱스 로드 실패: {e}")
        return []

def pick_courses_for_region(region: str, n: int = COURSE_RECOMMEND_COUNT) -> list[dict]:
    """
    web_courses_index_selenium.json 스키마(가변)를 관용적으로 파싱
    [{ "region":"제주", "title":"...", "thumb":"...", "url":"...", "desc":"..." }, ...]
    """
    region = _region_key(region)
    raw = _download_blob_json_by_name(COURSE_INDEX_BLOB_FILENAME)
    if not raw:
        return []

    def _get(d, keys, default=""):
        for k in keys:
            if k in d and d[k]:
                return d[k]
        return default

    # 지역 매칭(부분 포함 허용)
    cand = []
    for it in raw:
        r = _get(it, ["region","시도","지역","area"], "")
        if not r:
            continue
        rk = _region_key(str(r))
        if (region and region in rk) or (rk and rk in region) or (region == rk):
            cand.append(it)

    # 상위 n개 선택(단순)
    cand = cand[: max(n, 1)]

    out = []
    for it in cand[:n]:
        title = _get(it, ["title","name","코스명","course","코스","제목"], "코스")
        img   = _get(it, ["thumb","thumbnail","image","이미지","썸네일"], "")
        url   = _get(it, ["url","link","href","페이지","상세링크"], "")
        desc  = _get(it, ["desc","description","요약","소개"], "")
        out.append({"title": title, "thumbnail": img, "link": url, "desc": desc})
    return out

# ======================================================================================
# 메인 처리(한 번에) — 첫 답변은 '프리픽스'만 사용(괄호/장문 제거)
# ======================================================================================
async def process_chat(req):
    try:
        if 'audio' not in req.files:
            return jsonify(error="오디오 파일이 필요합니다."), 400

        api_key = (req.headers.get('X-API-KEY') or "").strip()
        tour_api_key = req.headers.get('X-TOUR-API-KEY')
        character = req.form.get('character', 'kei')
        client = get_openai_client(api_key)

        # 1) STT (요청대로 transcribe 모델 통일)
        audio_file = req.files['audio']
        stt_result = await client.audio.transcriptions.create(
            file=("audio.webm", audio_file.read()),
            model="gpt-4o-mini-transcribe",
            response_format="text"
        )
        user_text = stt_result or ""

        # 2) 관광지 검색
        search_service = SearchService(openai_api_key=api_key)
        recs = search_service.search(user_text, top_k=3, tour_api_key=tour_api_key, openai_api_key=api_key)

        # 3) 첫 답변: 프리픽스만 사용
        ai_text = _first_reply_prefix(recs) if recs else "관련 관광지를 아직 찾지 못했어요. 지역이나 키워드를 한 번만 더 알려줄래요?"
        ai_text = remove_empty_parentheses(remove_emojis(ai_text))

        # 4) TTS 생성 (캐릭터 낭독)
        audio_response = await client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=CHARACTER_VOICE[character],
            input=ai_text
        )
        audio_b64 = base64.b64encode(audio_response.content).decode()

        # 5) 대화 기록
        now_kst_iso = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        with history_lock:
            conversation_history.append({"role": "user", "content": user_text, "ts": now_kst_iso})
            conversation_history.append({"role": "assistant", "content": ai_text, "ts": now_kst_iso})
            if len(conversation_history) > HISTORY_MAX_LEN:
                conversation_history[:] = conversation_history[-HISTORY_MAX_LEN:]

        # 6) 로그 (비동기)
        log_data = {
            "timestamp": now_kst_iso,
            "character": character,
            "user_text": user_text,
            "ai_text": ai_text,
            "recommendations": recs
        }
        now = datetime.datetime.now(datetime.timezone.utc)
        blob_name = f"logs/{now.strftime('%Y-%m-%dT%H-%M-%SZ')}_{character}.json"
        asyncio.create_task(asyncio.to_thread(upload_log_to_vercel_blob, blob_name, log_data))

        return jsonify({
            "user_text": user_text,
            "ai_text": ai_text,
            "audio": audio_b64,
            "tour_recommendations": recs
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Failed to process request: {e}"}), 500

# ======================================================================================
# 스트리밍 처리 — meta(지역/카테고리) → token(프리픽스) → final 순서
# ======================================================================================
async def stream_chat(req):
    if 'audio' not in req.files:
        return jsonify(error="오디오 파일이 필요합니다."), 400

    api_key = (req.headers.get('X-API-KEY') or "").strip()
    tour_api_key = req.headers.get('X-TOUR-API-KEY')
    character = req.form.get('character', 'kei')
    client = get_openai_client(api_key)

    # 1) STT (모델 통일)
    audio_file = req.files['audio']
    stt_result = await client.audio.transcriptions.create(
        file=("audio.webm", audio_file.read()),
        model="gpt-4o-mini-transcribe",
        response_format="text"
    )
    user_text = stt_result or ""

    # 2) 관광지 검색
    search_service = SearchService(openai_api_key=api_key)
    recs = search_service.search(user_text, top_k=3, tour_api_key=tour_api_key, openai_api_key=api_key)

    # 3) 최종 텍스트는 프리픽스만
    final_text = _first_reply_prefix(recs) if recs else "관련 관광지를 아직 찾지 못했어요. 지역이나 키워드를 한 번만 더 알려줄래요?"
    final_text = remove_empty_parentheses(remove_emojis(final_text))

    # interim(중간멘트) 생성을 위해 프런트에 region/cat1 힌트도 같이 보냄
    region_hint = (recs[0].get("metadata") or {}).get("region") if recs else ""
    cat1_hint =    (recs[0].get("metadata") or {}).get("cat1")   if recs else ""

    async def event_stream():
        # (0) 메타 전송 → 프런트가 '시간 벌기 멘트'를 지역/카테고리 포함해 생성
        yield f"event: meta\ndata: {json.dumps({'region': region_hint or '', 'cat1': cat1_hint or ''}, ensure_ascii=False)}\n\n"

        # (1) 프리픽스를 바로 토큰으로 먼저 송출
        yield f"event: token\ndata: {json.dumps({'token': final_text + '\\n\\n'}, ensure_ascii=False)}\n\n"

        # (2) TTS 생성
        audio_b64 = ""
        try:
            audio_response = await client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=CHARACTER_VOICE[character],
                input=final_text
            )
            audio_b64 = base64.b64encode(audio_response.content).decode()
        except Exception:
            pass

        # (3) 최종 패킷
        payload = {
            "ai_text": final_text,
            "audio": audio_b64,
            "tour_recommendations": recs
        }
        yield f"event: final\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
