# scripts/routes.py
import time
import base64
from flask import render_template, request, Blueprint, jsonify

from scripts.services import process_chat, stream_chat, pick_courses_for_region
from scripts.config import CHARACTER_VOICE
from openai import OpenAI   # ← 동기 클라이언트 사용

bp = Blueprint("api", __name__)

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/scripts/chat', methods=['POST'])
    def chat_once():
        import asyncio
        return asyncio.run(process_chat(request))

    @app.route('/scripts/chat_stream', methods=['POST'])
    def chat_stream():
        import asyncio
        return asyncio.run(stream_chat(request))

    # ▼▼▼ 교체한 부분: 코스 + (옵션) gpt-4o-mini-tts 음성 동시 반환 ▼▼▼
    @app.route('/scripts/courses', methods=['GET'])
    def get_courses():
        region = request.args.get('region', '').strip()
        try:
            n = int(request.args.get('n', '3'))
        except Exception:
            n = 3

        # TTS에 사용할 캐릭터 (기본: kei)
        character = request.args.get('character', 'kei').strip() or 'kei'

        courses = pick_courses_for_region(region, n)

        # 두 번째 멘트(요청하신 문구)
        say_text = "원하는 대로 추천 관광 코스 정보를 가져왔어. 아래 카드에서 자세한 내용을 확인해 봐!"

        # 헤더에 API 키가 있으면 gpt-4o-mini-tts로 음성 생성
        audio_b64 = ""
        api_key = (request.headers.get('X-API-KEY') or "").strip()
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                audio_resp = client.audio.speech.create(
                    model="gpt-4o-mini-tts",
                    voice=CHARACTER_VOICE.get(character) or "alloy",
                    input=say_text
                )
                audio_b64 = base64.b64encode(audio_resp.content).decode()
            except Exception as e:
                print(f"[courses] TTS 생성 실패: {e}")

        return jsonify({
            "region": region,
            "count": len(courses),
            "courses": courses,
            "say_text": say_text,
            "audio": audio_b64   # ← chat.js에서 입모양 연동해 재생
        }), 200
