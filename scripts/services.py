import base64
import asyncio
import threading
import json
import requests
import datetime
import time
from typing import Dict, Any, List, Optional

from flask import jsonify, abort, request, Response, stream_with_context
from openai import AsyncOpenAI

from scripts.config import (
    VERCEL_TOKEN, VERCEL_PROJ_ID,
    CHARACTER_SYSTEM_PROMPTS, CHARACTER_VOICE,
    HISTORY_MAX_LEN
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
            model="gpt-4o-mini-transcribe", # whisper-1
            response_format="text"
        )
        user_text = stt_result or ""

        # 2) 관광지 검색  ✅ API 키 주입
        search_service = SearchService(openai_api_key=api_key)
        recommendations = search_service.search(
            user_text, top_k=5, tour_api_key=tour_api_key, openai_api_key=api_key
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

    # 2) 관광지 검색  ✅ API 키 주입
    search_service = SearchService(openai_api_key=api_key)
    recommendations = search_service.search(user_text, top_k=5, tour_api_key=tour_api_key, openai_api_key=api_key)

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
