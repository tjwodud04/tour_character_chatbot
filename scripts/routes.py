import time
from flask import render_template, request, Blueprint, jsonify

# 관광지 추천 채팅 처리
from scripts.services import process_chat, stream_chat

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

    # 지역별 관광 코스(Blob JSON) 제공
    @app.route('/scripts/courses', methods=['GET'])
    def get_courses():
        """?region=제주&n=3  →  { region, count, courses:[{title,thumbnail,link,desc}, ...] }"""
        region = (request.args.get('region') or "").strip()
        n = int(request.args.get('n') or 3)
        if not region:
            return jsonify({"error":"region required"}), 400
        try:
            from scripts.services import pick_courses_for_region
            courses = pick_courses_for_region(region, n)
            return jsonify({"region": region, "count": len(courses), "courses": courses})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
