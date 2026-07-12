"""Flask 라우트 등록.

엔드포인트 계약(경로/메서드/응답 형태)은 프런트엔드와의 계약이므로 그대로 유지한다.
- POST /scripts/chat         : 오디오 → 관광지 추천(JSON 한 번에)
- POST /scripts/chat_stream  : 오디오 → 관광지 추천(SSE 스트리밍)
- GET  /scripts/courses      : 지역별 추천 코스(+선택적 TTS 음성)
"""

import asyncio
import base64

from flask import Flask, jsonify, render_template, request
from openai import OpenAI  # 동기 클라이언트(코스 TTS용)

from scripts.config import (
    CHARACTER_VOICE,
    COURSE_READY_MESSAGE,
    COURSE_RECOMMEND_COUNT,
    DEFAULT_CHARACTER,
    DEFAULT_TTS_VOICE,
    OPENAI_TTS_MODEL,
)
from scripts.services import pick_courses_for_region, process_chat, stream_chat


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/scripts/chat", methods=["POST"])
    def chat_once():
        return asyncio.run(process_chat(request))

    @app.route("/scripts/chat_stream", methods=["POST"])
    def chat_stream():
        return asyncio.run(stream_chat(request))

    @app.route("/scripts/courses", methods=["GET"])
    def get_courses():
        region = request.args.get("region", "").strip()
        try:
            n = int(request.args.get("n", str(COURSE_RECOMMEND_COUNT)))
        except Exception:
            n = COURSE_RECOMMEND_COUNT

        # TTS에 사용할 캐릭터 (기본: kei)
        character = request.args.get("character", DEFAULT_CHARACTER).strip() or DEFAULT_CHARACTER

        courses = pick_courses_for_region(region, n)
        say_text = COURSE_READY_MESSAGE

        # 헤더에 API 키가 있으면 TTS로 음성 생성
        audio_b64 = ""
        api_key = (request.headers.get("X-API-KEY") or "").strip()
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                audio_resp = client.audio.speech.create(
                    model=OPENAI_TTS_MODEL,
                    voice=CHARACTER_VOICE.get(character) or DEFAULT_TTS_VOICE,
                    input=say_text,
                )
                audio_b64 = base64.b64encode(audio_resp.content).decode()
            except Exception as exc:
                print(f"[courses] TTS 생성 실패: {exc}")

        return jsonify({
            "region": region,
            "count": len(courses),
            "courses": courses,
            "say_text": say_text,
            "audio": audio_b64,  # chat.js에서 입모양 연동해 재생
        }), 200
