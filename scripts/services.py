import base64
import asyncio
import threading
import json
import requests
import datetime
import time
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from flask import jsonify, abort, request, Response, stream_with_context
from openai import AsyncOpenAI

from scripts.config import (
    VERCEL_TOKEN, VERCEL_PROJ_ID,
    CHARACTER_SYSTEM_PROMPTS, CHARACTER_VOICE,
    HISTORY_MAX_LEN,
    VERCEL_BLOB_TOKEN, COURSE_INDEX_BLOB_FILENAME, COURSE_RECOMMEND_COUNT
)
from scripts.utils import (
    remove_empty_parentheses, markdown_to_html_links,
    extract_first_markdown_url, remove_emojis
)
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
# 신규: 첫 답변 머리말 & 지역 코스(Blob) 유틸
# ======================================================================================
def _first_reply_prefix(recommendations: list[dict]) -> str:
    """
    '<지역> 관광지(이름1, 이름2, 이름3)를 추천해요. 조금 더 자세한 내용은 아래의 카드를 참고해주세요.
     원하시면 지역과 관련된 관광 코스도 추천해줄 수 있는데, 보여드릴까요?'
    """
    if not recommendations:
        return ""
    names = [ (rec.get("name") or "").strip() for rec in recommendations if rec.get("name") ]
    names = names[:3]
    region = (recommendations[0].get("metadata") or {}).get("region") or ""
    region_part = f"{region} " if region else ""
    if names:
        names_str = ", ".join(names)
        return (
            f"{region_part}관광지({names_str})를 추천해요. "
            f"조금 더 자세한 내용은 아래의 카드를 참고해주세요.\n\n"
            f"원하시면 지역과 관련된 관광 코스도 추천해줄 수 있는데, 보여드릴까요?"
        )
    return (
        f"{region_part}관광지를 추천해요. "
        f"조금 더 자세한 내용은 아래의 카드를 참고해주세요.\n\n"
        f"원하시면 지역과 관련된 관광 코스도 추천해줄 수 있는데, 보여드릴까요?"
    )

def _region_key(s: str) -> str:
    if not s: return ""
    s = s.replace("특별자치도","").replace("광역시","").replace("특별시","").strip()
    return s

def _download_blob_json_by_name(blob_filename: str) -> list[dict]:
    """
    Vercel Blob API(v2) 목록 조회 → filename 기준으로 downloadUrl 획득 → JSON 로드
    """
    if not VERCEL_BLOB_TOKEN:
        raise RuntimeError("VERCEL_BLOB_TOKEN 이(가) 설정되지 않았습니다.")
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
        ctype = (r2.headers.get("Content-Type") or "").lower()
        return r2.json() if ctype.startswith("application/json") else []
    except Exception as e:
        print(f"[Blob] 코스 인덱스 로드 실패: {e}")
        return []

def pick_courses_for_region(region: str, n: int = COURSE_RECOMMEND_COUNT) -> list[dict]:
    """
    web_courses_index_selenium.json 예시 스키마(탄력적 매핑):
    [{"region":"제주","title":"...", "thumb":"...", "url":"...", "desc":"..."}, ...]
    → [{title, thumbnail, link, desc}]로 정규화
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

    cand = []
    for it in raw:
        r = _get(it, ["region","시도","지역","area"], "")
        if not r:
            continue
        rk = _region_key(str(r))
        if (region and region in rk) or (rk and rk in region) or (region == rk):
            cand.append(it)

    cand = cand[: max(n, 1)]

    out = []
    for it in cand[:n]:
        title = _get(it, ["title","name","코스명","course","코스","제목"], "코스")
        img   = _get(it, ["thumb","thumbnail","image","이미지","썸네일"], "")
        url   = _get(it, ["url","link","href","페이지","상세링크"], "")
        desc  = _get(it, ["desc","description","요약","소개"], "")
        out.append({
            "title": title,
            "thumbnail": img,
            "link": url,
            "desc": desc
        })
    return out

# ======================================================================================
# 메인 처리(관광지 추천 채팅)
# ======================================================================================
async def process_chat(req):
    try:
        if 'audio' not in req.files:
            return jsonify(error="오디오 파일이 필요합니다."), 400

        api_key = (req.headers.get('X-API-KEY') or "").strip()
        tour_api_key = req.headers.get('X-TOUR-API-KEY')
        character = req.form.get('character', 'kei')
        client = get_openai_client(api_key)

        # 1) Whisper STT
        audio_file = req.files['audio']
        stt_result = await client.audio.transcriptions.create(
            file=("audio.webm", audio_file.read()),
            model="gpt-4o-mini-transcribe",  # whisper-1 대체
            response_format="text"
        )
        user_text = stt_result or ""

        # 2) 관광지 검색
        search_service = SearchService(openai_api_key=api_key)
        recommendations = search_service.search(
            user_text, top_k=3, tour_api_key=tour_api_key, openai_api_key=api_key
        )

        # 3) 캐릭터 응답 생성
        system_prompt = CHARACTER_SYSTEM_PROMPTS[character]
        with history_lock:
            messages = [{"role": "system", "content": system_prompt}] + conversation_history[-HISTORY_MAX_LEN:]

        if recommendations:
            tour_context = "추천된 관광지 정보:\n"
            for i, rec in enumerate(recommendations, 1):
                tour_context += f"{i}. {rec['name']} - {rec.get('reason', '')}\n"
            user_prompt = f"{user_text}\n\n{tour_context}\n\n위 관광지들을 참고해서 친근하게 추천해주세요. 2-3문장으로 간단히 설명해주세요."
        else:
            user_prompt = f"{user_text}\n\n관련 관광지를 찾지 못했습니다. 다른 지역이나 키워드로 다시 물어봐 달라고 안내해주세요."

        messages.append({"role": "user", "content": user_prompt})

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=512,
        )
        ai_text = response.choices[0].message.content or ""
        ai_text = remove_emojis(ai_text) or "죄송해요, 답변을 준비하지 못했어요. 다시 한 번 말씀해주시겠어요?"

        # [ADD] 첫 답변 머리말 붙이기
        if recommendations:
            prefix = _first_reply_prefix(recommendations)
            if prefix:
                ai_text = f"{prefix}\n\n{ai_text}"

        # 4) TTS 생성
        tts_text = remove_emojis(ai_text)
        audio_response = await client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=CHARACTER_VOICE[character],
            input=tts_text
        )
        audio_b64 = base64.b64encode(audio_response.content).decode()

        # 5) 대화 기록 갱신
        now_kst_iso = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        with history_lock:
            conversation_history.append({"role": "user", "content": user_text, "ts": now_kst_iso})
            conversation_history.append({"role": "assistant", "content": ai_text, "ts": now_kst_iso})
            if len(conversation_history) > HISTORY_MAX_LEN:
                conversation_history[:] = conversation_history[-HISTORY_MAX_LEN:]

        # 6) 로그 업로드 (비동기)
        log_data = {
            "timestamp": now_kst_iso,
            "character": character,
            "user_text": user_text,
            "ai_text": ai_text,
            "recommendations": recommendations
        }
        now = datetime.datetime.now(datetime.timezone.utc)
        blob_name = f"logs/{now.strftime('%Y-%m-%dT%H-%M-%SZ')}_{character}.json"
        asyncio.create_task(asyncio.to_thread(upload_log_to_vercel_blob, blob_name, log_data))

        # 응답
        return jsonify({
            "user_text": user_text,
            "ai_text": remove_empty_parentheses(ai_text),
            "audio": audio_b64,
            "tour_recommendations": recommendations
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Failed to process request: {e}"}), 500

# ======================================================================================
# 스트리밍 처리
# ======================================================================================
async def stream_chat(req):
    """
    토큰 단위로 전송 후, 마지막에 최종 패킷(ai_text, audio_b64, tour_recommendations) 송신
    """
    if 'audio' not in req.files:
        return jsonify(error="오디오 파일이 필요합니다."), 400

    api_key = (req.headers.get('X-API-KEY') or "").strip()
    tour_api_key = req.headers.get('X-TOUR-API-KEY')
    character = req.form.get('character', 'kei')
    client = get_openai_client(api_key)

    # 1) STT
    audio_file = req.files['audio']
    stt_result = await client.audio.transcriptions.create(
        file=("audio.webm", audio_file.read()),
        model="whisper-1",
        response_format="text"
    )
    user_text = stt_result or ""

    # 2) 관광지 검색
    search_service = SearchService(openai_api_key=api_key)
    recommendations = search_service.search(user_text, top_k=3, tour_api_key=tour_api_key, openai_api_key=api_key)

    # 3) 스트리밍용 메시지 구성
    system_prompt = CHARACTER_SYSTEM_PROMPTS[character]
    with history_lock:
        messages = [{"role": "system", "content": system_prompt}] + conversation_history[-HISTORY_MAX_LEN:]

        if recommendations:
            tour_context = "추천된 관광지 정보:\n"
            for i, rec in enumerate(recommendations, 1):
                tour_context += f"{i}. {rec['name']} - {rec.get('reason', '')}\n"
            user_prompt = f"{user_text}\n\n{tour_context}\n\n위 관광지들을 참고해서 친근하게 추천해주세요."
        else:
            user_prompt = f"{user_text}\n\n관련 관광지를 찾지 못했습니다. 다른 키워드로 다시 물어봐 달라고 안내해주세요."

        messages.append({"role": "user", "content": user_prompt})

    async def event_stream():
        # [ADD] 프리픽스 먼저 흘려보내기
        if recommendations:
            prefix = _first_reply_prefix(recommendations)
            if prefix:
                yield f"event: token\ndata: {json.dumps({'token': prefix + '\\n\\n'}, ensure_ascii=False)}\n\n"

        # LLM 스트림
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=512,
            stream=True
        )
        full_text: List[str] = []

        async for chunk in stream:
            delta = chunk.choices[0].delta.get("content")
            if delta:
                full_text.append(delta)
                yield f"event: token\ndata: {json.dumps({'token': delta}, ensure_ascii=False)}\n\n"

        final_text = "".join(full_text).strip() or "죄송해요, 답변을 준비하지 못했어요."
        final_text_noemoji = remove_emojis(final_text)

        # TTS 생성
        audio_b64 = ""
        try:
            audio_response = await client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice=CHARACTER_VOICE[character],
                input=final_text_noemoji
            )
            audio_b64 = base64.b64encode(audio_response.content).decode()
        except Exception:
            pass

        # 최종 패킷
        payload = {
            "ai_text": final_text_noemoji,
            "audio": audio_b64,
            "tour_recommendations": recommendations
        }
        yield f"event: final\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")
