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
    CHARACTER_SYSTEM_PROMPTS, CHARACTER_VOICE,
    HISTORY_MAX_LEN,
    VERCEL_BLOB_TOKEN, COURSE_INDEX_BLOB_FILENAME, COURSE_RECOMMEND_COUNT,
    VERCEL_BLOB_PUBLIC_BASE
)
from scripts.utils import remove_empty_parentheses, remove_emojis, copula_iy_a
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
        print("[log] Vercel ENV 미설정: 로그 업로드 생략")
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
# 유틸: 첫 답변 프리픽스 & 코스 로딩
# ======================================================================================
def _first_reply_prefix(recs: list[dict], character: str = "kei") -> str:
    """관광지는 괄호 없이 콤마로 나열하고, 캐릭터별 톤을 달리해 첫 답변 문구를 구성."""
    if not recs:
        return ""
    names = [ (r.get("name") or "").strip() for r in recs if r.get("name") ]
    names = [n for n in names if n][:3]
    names_str = ", ".join(names) if names else "관광지"
    # 마지막 명사를 기준으로 '이야/야' 선택
    last_name = names[-1] if names else "관광지"
    cop = copula_iy_a(last_name)

    if character == "kei":
        # 요청한 Kei 전용 문구
        return (
            f"추천하는 관광지는 {names_str}{cop}! "
            f"더 자세한 내용은 아래의 카드를 참고해 줘. "
            f"추가로, 추천 관광 코스도 보여줄 수 있는데, 원해?"
        )
    else:
        # Haru 등은 기존 톤 유지(간결)
        return (
            f"관광지 {names_str}{cop} 추천입니다. "
            f"자세한 내용은 아래 카드를 참고해 주세요. "
            f"원하시면 관련 관광 코스도 제안해 드릴까요?"
        )

def _region_key(s: str) -> str:
    if not s: return ""
    return s.replace("특별자치도","").replace("광역시","").replace("특별시","").strip()

def _download_blob_json_by_name(blob_filename: str) -> list[dict]:
    base = (VERCEL_BLOB_PUBLIC_BASE or "").rstrip("/")
    if not base:
        return []
    url = f"{base}/{blob_filename.lstrip('/')}"
    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "json" in ctype:
            data = r.json()
        else:
            data = json.loads(r.text or "[]")
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[Blob] 코스 인덱스 로드 실패: {e}")
        return []

def pick_courses_for_region(region: str, n: int = COURSE_RECOMMEND_COUNT) -> list[dict]:
    raw = _download_blob_json_by_name(COURSE_INDEX_BLOB_FILENAME)
    if not raw:
        return []

    def _norm_region(s: str) -> str:
        s = (s or "").strip()
        return s.replace("특별자치도","").replace("광역시","").replace("특별시","").replace("도","").strip()

    def _get(d: dict, keys: list[str], default=""):
        for k in keys:
            if d.get(k):
                return d[k]
        return default

    want = _norm_region(region)
    picked = []
    for it in raw:
        loc = _get(it, ["location","지역","시도","area"], "")
        locn = _norm_region(str(loc))
        if not want or (want in locn) or (locn in want):
            title = _get(it, ["title","name","코스명","제목"], "코스")
            thumb = _get(it, ["thumbnail","thumb","image","이미지"], "")
            link  = _get(it, ["course_url","url","link","href"], "")
            spots = it.get("spots") if isinstance(it.get("spots"), list) else []
            desc  = " · ".join([str(s) for s in spots[:3]]) if spots else ""
            picked.append({"title": str(title), "thumbnail": str(thumb), "link": str(link), "desc": str(desc)})
            if len(picked) >= n:
                break
    return picked

# ======================================================================================
# 메인 처리(한 번에)
# ======================================================================================
async def process_chat(req):
    try:
        if 'audio' not in req.files:
            return jsonify(error="오디오 파일이 필요합니다."), 400

        api_key = (req.headers.get('X-API-KEY') or "").strip()
        tour_api_key = req.headers.get('X-TOUR-API-KEY')
        character = req.form.get('character', 'kei')
        client = get_openai_client(api_key)

        # STT (단일 모델로 통일)
        audio_file = req.files['audio']
        stt_result = await client.audio.transcriptions.create(
            file=("audio.webm", audio_file.read()),
            model="gpt-4o-mini-transcribe",
            response_format="text"
        )
        user_text = stt_result or ""

        # 관광지 검색
        search_service = SearchService(openai_api_key=api_key)
        recs = search_service.search(user_text, top_k=3, tour_api_key=tour_api_key, openai_api_key=api_key)

        # 첫 답변 문구(캐릭터별)
        ai_text = _first_reply_prefix(recs, character) if recs else "관련 관광지를 아직 찾지 못했어. 지역이나 키워드를 한 번만 더 알려줄래?"
        ai_text = remove_empty_parentheses(remove_emojis(ai_text))

        # TTS
        audio_response = await client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=CHARACTER_VOICE[character],
            input=ai_text
        )
        audio_b64 = base64.b64encode(audio_response.content).decode()

        # 히스토리
        now_kst_iso = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        with history_lock:
            conversation_history.append({"role": "user", "content": user_text, "ts": now_kst_iso})
            conversation_history.append({"role": "assistant", "content": ai_text, "ts": now_kst_iso})
            if len(conversation_history) > HISTORY_MAX_LEN:
                conversation_history[:] = conversation_history[-HISTORY_MAX_LEN:]

        # 로그
        now = datetime.datetime.now(datetime.timezone.utc)
        blob_name = f"logs/{now.strftime('%Y-%m-%dT%H-%M-%SZ')}_{character}.json"
        log_data = {"timestamp": now_kst_iso, "character": character, "user_text": user_text, "ai_text": ai_text, "recommendations": recs}
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
# 스트리밍 처리
# ======================================================================================
async def stream_chat(req):
    if 'audio' not in req.files:
        return jsonify(error="오디오 파일이 필요합니다."), 400

    api_key = (req.headers.get('X-API-KEY') or "").strip()
    tour_api_key = req.headers.get('X-TOUR-API-KEY')
    character = req.form.get('character', 'kei')
    client = get_openai_client(api_key)

    # STT
    audio_file = req.files['audio']
    stt_result = await client.audio.transcriptions.create(
        file=("audio.webm", audio_file.read()),
        model="gpt-4o-mini-transcribe",
        response_format="text"
    )
    user_text = stt_result or ""

    # 검색
    search_service = SearchService(openai_api_key=api_key)
    recs = search_service.search(user_text, top_k=3, tour_api_key=tour_api_key, openai_api_key=api_key)

    # 최종 텍스트(캐릭터별)
    final_text = _first_reply_prefix(recs, character) if recs else "관련 관광지를 아직 찾지 못했어. 지역이나 키워드를 한 번만 더 알려줄래?"
    final_text = remove_empty_parentheses(remove_emojis(final_text))

    # 지역/카테고리 힌트
    region_hint = (recs[0].get("metadata") or {}).get("region") if recs else ""
    cat1_hint =    (recs[0].get("metadata") or {}).get("cat1")   if recs else ""

    async def event_stream():
        # 1) 메타: region/cat1 힌트
        yield f"event: meta\ndata: {json.dumps({'region': region_hint or '', 'cat1': cat1_hint or ''}, ensure_ascii=False)}\n\n"
        # 2) 프리픽스 토큰: 완성 텍스트를 한 번에 흘려 UI 스켈레톤 채움
        newlines = '\n\n'
        yield f"event: token\ndata: {json.dumps({'token': final_text + newlines}, ensure_ascii=False)}\n\n"

        # 3) TTS: gpt-4o-mini-tts로 음성 생성 (실패 시 무음)
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

        payload = {
            "ai_text": final_text,
            "audio": audio_b64,
            "tour_recommendations": recs
        }
        yield f"event: final\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
