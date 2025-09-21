import time
from flask import render_template, request, Blueprint, jsonify

# 관광지 추천 채팅 처리
from scripts.services import process_chat, stream_chat, pick_courses_for_region

bp = Blueprint("api", __name__)

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    # 기존: 한 번에 JSON으로 응답
    @app.route('/scripts/chat', methods=['POST'])
    async def chat_once():
        return await process_chat(request)

    # 스트리밍 응답 (SSE 스타일, 토큰/최종 패킷 순차 수신)
    @app.route('/scripts/chat_stream', methods=['POST'])
    async def chat_stream():
        return await stream_chat(request)

     # ▼▼▼ 추가: 지역 코스 조회 (Vercel Blob에서 JSON 읽기) ▼▼▼
    @app.route('/scripts/courses', methods=['GET'])
    def get_courses():
        region = request.args.get('region', '').strip()
        try:
            n = int(request.args.get('n', '3'))
        except Exception:
            n = 3
        courses = pick_courses_for_region(region, n)
        return jsonify({"region": region, "count": len(courses), "courses": courses}), 200
