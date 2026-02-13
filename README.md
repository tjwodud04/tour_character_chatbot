# Live2D Korea Tour Guide (Flask + OpenAI + TourAPI)

[🇰🇷 한국어](#-한국어) | [🇺🇸 English](#-english)

Intro Video: 



https://github.com/user-attachments/assets/d8a38dda-6076-4ff1-8e53-be846d26a57d



---

## 🇰🇷 한국어

한국 관광 특화 음성 어시스턴트 데모입니다.  
**Live2D 아바타**와 **음성 입·출력(STT/TTS)**, **한국관광공사 TourAPI**를 연동하여
자연어 음성 질의 → 관광지 추천 카드/코스 제안 → 아바타 립싱크까지 한 번에 보여줍니다.

- **Frontend**: PIXI + Live2D (Kei/Haru), 카카오톡 스타일 대화 UI
- **Backend**: Flask(API) + OpenAI SDK(v1) + TourAPI, SSE 스트리밍
- **Search**: OpenAI Embedding + Redis 캐시
- **Deploy**: Vercel (정적/파이썬 혼합, `vercel.json`)

---

## ✨ 주요 기능

- 🎙️ **음성 질의(STT)**: `gpt-4o-mini-transcribe`로 브라우저 녹음 음성 인식
- 🗺️ **관광지 추천**: OpenAI로 `(region, cat1)` 추출 → TourAPI로 후보 수집/필터링/요약
- 🧠 **임베딩 캐시**: 동일/유사 질의는 Redis 캐시에 저장해 빠르게 응답
- 🗣️ **음성 응답(TTS)**: `gpt-4o-mini-tts`로 캐릭터 보이스(Kei/Haru) 생성, Live2D 립싱크
- 🔄 **스트리밍 응답**: `/scripts/chat_stream` SSE로 메타 → 토큰 → 최종 페이로드 순차 전송
- 🧩 **코스 제안**: `/scripts/courses`에서 지역별 코스 카드 + TTS 멘트까지 한번에

---

## 📁 디렉터리 구조

```
front/
  css/               # main.css, style.css (채팅/카드/반응형)
  js/
    chat.js          # UI 로직, 녹음/스트림, 카드 렌더, Sanitizer
  kei.html           # Kei 캐릭터 페이지
  index.html         # 진입 페이지(예시)
model/               # Live2D 모델(asset)
scripts/
  app.py             # Flask 엔트리
  routes.py          # 라우팅 & API 엔드포인트
  services.py        # STT/TTS, SSE, 코스 인덱스 로드, 로그 업로드
  data_service.py    # TourAPI 연동/후처리/요약/이미지 검증
  search_service.py  # Redis 임베딩 캐시 ↔ DataService
  embedding_service.py
  utils.py
  config.py          # 모든 환경변수/상수 설정
  vercel.json        # Vercel 빌드/라우팅 설정
```

---

## 🔧 빠른 시작 (로컬)

### 0) 사전 준비
- Python 3.11+
- (선택) Redis 서버
- OpenAI API Key
- TourAPI Key (한국관광공사)

### 1) 설치
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) 환경 변수 설정
`.env` 파일을 만들어 아래와 같이 채우거나, 쉘에 직접 export 해주세요.

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# 한국관광공사 TourAPI
KOREA_TOURISM_API_KEY=발급키

# Redis (선택: 캐시 사용)
REDIS_URL=redis://localhost:6379

# Vercel Blob 로그(선택)
VERCEL_TOKEN=
VERCEL_PROJECT_ID=
VERCEL_BLOB_PUBLIC_BASE=https://<your>.public.blob.vercel-storage.com
BLOB_READ_WRITE_TOKEN=

# 코스 인덱스(선택): 퍼블릭 JSON 주소
COURSE_INDEX_FULL_URL=https://.../web_courses_index_selenium.json
COURSE_INDEX_BLOB_FILENAME=web_courses_index_selenium.json
```

> **브라우저에서 호출할 API 키 전송**  
> `front/js/chat.js`는 요청 헤더에 `X-API-KEY`, `X-TOUR-API-KEY`를 붙이기 위해  
> `localStorage.openai_api_key`, `localStorage.tour_api_key`를 읽습니다.
> 개발 중엔 콘솔에서 다음처럼 저장하세요:
> ```js
> localStorage.setItem('openai_api_key','sk-...'); 
> localStorage.setItem('tour_api_key','발급키');
> ```

### 3) 실행
```bash
python scripts/app.py
# http://localhost:8001 접속 → Kei 페이지는 /kei.html
```

---

## 🚀 배포 (Vercel)

이미 `scripts/vercel.json`이 포함되어 있어 **정적(front/ & model/)** 과 **파이썬(scripts/app.py)** 을 함께 배포합니다.

1) Vercel 프로젝트 생성  
2) 환경변수 탭에 README의 변수를 등록(특히 `OPENAI_API_KEY`, `KOREA_TOURISM_API_KEY`)  
3) 배포 후 도메인 접속

> Blob 기반 로그/코스 JSON을 쓰려면 `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_BLOB_PUBLIC_BASE`(퍼블릭 버킷 URL)도 등록하세요.

---

## 🔌 API 엔드포인트

### `POST /scripts/chat`
- 음성 1회 전송 → STT → 추천 → TTS까지 **단발 응답**
- 헤더  
  - `X-API-KEY`: OpenAI 키  
  - `X-TOUR-API-KEY`: TourAPI 키
- 폼 데이터  
  - `audio` (webm/opus), `character` in {`kei`,`haru`}
- 응답
```json
{
  "user_text": "제주도 자연 관광지 알려줘",
  "ai_text": "추천하는 관광지는 ...",
  "audio": "<base64 webm>",
  "tour_recommendations": [ { "name": "...", "homepage": "...", "map_url": "...", "metadata": {...} } ]
}
```

### `POST /scripts/chat_stream`
- **SSE 스트리밍**: `meta` → `token` → `final` 이벤트 순서
- 이벤트 데이터 구조는 `front/js/chat.js`의 파서에 맞춤

### `GET /scripts/courses?region=제주&n=3&character=kei`
- 코스 카드 + **두 번째 멘트** + (키 제공 시) **TTS 오디오**
- 헤더: `X-API-KEY` (있으면 TTS 생성)

---

## ⚙️ 구성/동작 개요

1. 브라우저가 `MediaRecorder(audio/webm;codecs=opus)`로 녹음
2. `/scripts/chat(_stream)`에 업로드 → `gpt-4o-mini-transcribe`로 STT
3. 쿼리 임베딩 → Redis 캐시 조회 → 미스면 TourAPI 호출/정제/요약
4. 첫 응답을 `gpt-4o-mini-tts`로 합성 → Base64 오디오 반환
5. Live2D 모델이 오디오를 재생하며 **립싱크 파라미터(ParamMouthOpenY)** 갱신
6. 사용자가 “예”를 누르면 `/scripts/courses`에서 지역 코스/오디오 동시 제공

---

## 🔐 보안/운영 메모

- **브라우저에서 키를 다루기 때문에**, 실제 제품에서는 프록시/토큰 화 등으로 키를 직접 노출하지 않도록 하세요.
- 이미지 URL은 **확장자/도메인/HEAD 응답**을 검사하여 안전하지 않은 링크를 걸러냅니다(`data_service.py`).
- Sanitizer는 **`<a>`/`<br>`만 허용**하며, `href/target/rel` 외 속성 제거.

---

## 📝 라이선스 / 크레딧

- Live2D 모델/에셋 라이선스는 해당 소유자 약관을 따릅니다.
- TourAPI: 한국관광공사 OpenAPI 약관 준수
- OpenAI: 서비스 약관/정책 준수
---

## 🇺🇸 English

# Live2D Korea Tour Guide (Flask + OpenAI + TourAPI)

A demo of a **voice-based tourist assistant** for Korea.  
It integrates **Live2D avatars**, **speech input/output (STT/TTS)**, and the **Korea Tourism Organization TourAPI** to provide an end-to-end experience:  
voice query → recommendation cards & course suggestions → avatar lip-sync playback.

- **Frontend**: PIXI + Live2D (Kei/Haru), KakaoTalk-style chat UI  
- **Backend**: Flask(API) + OpenAI SDK(v1) + TourAPI, SSE streaming  
- **Search**: OpenAI Embedding + Redis cache  
- **Deploy**: Vercel (static + Python, `vercel.json`)  

---

## ✨ Features

- 🎙️ **Voice Query (STT)**: Uses `gpt-4o-mini-transcribe` for browser audio transcription  
- 🗺️ **Tour Recommendations**: Extracts `(region, cat1)` with OpenAI → queries TourAPI → filters & summarizes results  
- 🧠 **Embedding Cache**: Caches similar queries in Redis for faster responses  
- 🗣️ **Voice Response (TTS)**: `gpt-4o-mini-tts` generates Kei/Haru voices + Live2D lip-sync  
- 🔄 **Streaming Response**: `/scripts/chat_stream` with SSE events (meta → token → final)  
- 🧩 **Course Suggestions**: `/scripts/courses` returns region-specific course cards + voice narration  

---

## 📁 Project Structure

```
front/
  css/               # main.css, style.css (chat/cards/responsive)
  js/
    chat.js          # UI logic, recording/streaming, card rendering, sanitizer
  kei.html           # Kei character page
  index.html         # Entry page (example)
model/               # Live2D assets
scripts/
  app.py             # Flask entry
  routes.py          # Routing & API endpoints
  services.py        # STT/TTS, SSE, course index loader, log uploader
  data_service.py    # TourAPI integration, filtering, summarization, image validation
  search_service.py  # Redis cache ↔ DataService
  embedding_service.py
  utils.py
  config.py          # Env variables & constants
  vercel.json        # Vercel deployment config
```

---

## 🔧 Quick Start (Local)

### 0) Prerequisites
- Python 3.11+
- (Optional) Redis server
- OpenAI API Key
- TourAPI Key (KTO)

### 1) Install
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Environment Variables
Create a `.env` file or export them in your shell:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# KTO TourAPI
KOREA_TOURISM_API_KEY=your_key_here

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Vercel Blob (optional)
VERCEL_TOKEN=
VERCEL_PROJECT_ID=
VERCEL_BLOB_PUBLIC_BASE=https://<your>.public.blob.vercel-storage.com
BLOB_READ_WRITE_TOKEN=

# Course index (optional)
COURSE_INDEX_FULL_URL=https://.../web_courses_index_selenium.json
COURSE_INDEX_BLOB_FILENAME=web_courses_index_selenium.json
```

> **Browser API Key Usage**  
> `front/js/chat.js` reads `localStorage.openai_api_key` and `localStorage.tour_api_key`  
> to attach headers (`X-API-KEY`, `X-TOUR-API-KEY`) in requests.  
> Set them in DevTools console:  
> ```js
> localStorage.setItem('openai_api_key','sk-...'); 
> localStorage.setItem('tour_api_key','your_key');
> ```

### 3) Run
```bash
python scripts/app.py
# Open http://localhost:8001 → Kei demo: /kei.html
```

---

## 🚀 Deploy (Vercel)

This repo includes `scripts/vercel.json` for deploying static (front/, model/) + Python (scripts/app.py).

1. Create a Vercel project  
2. Add environment variables (at least `OPENAI_API_KEY`, `KOREA_TOURISM_API_KEY`)  
3. Deploy and open the domain  

> For Blob-based logs/course JSON, also set `VERCEL_TOKEN`, `VERCEL_PROJECT_ID`, `VERCEL_BLOB_PUBLIC_BASE`.

---

## 🔌 API Endpoints

### `POST /scripts/chat`
- Single audio → STT → recommendation → TTS (one-shot response)
- Headers:
  - `X-API-KEY`: OpenAI key
  - `X-TOUR-API-KEY`: TourAPI key
- Form data:
  - `audio` (webm/opus), `character` in {`kei`,`haru`}
- Response:
```json
{
  "user_text": "Recommend nature spots in Jeju",
  "ai_text": "Suggested destinations are ...",
  "audio": "<base64 webm>",
  "tour_recommendations": [ { "name": "...", "homepage": "...", "map_url": "...", "metadata": {...} } ]
}
```

### `POST /scripts/chat_stream`
- **SSE stream**: events in order `meta` → `token` → `final`  
- Matches `chat.js` parser logic

### `GET /scripts/courses?region=Jeju&n=3&character=kei`
- Returns course cards + narration (TTS if `X-API-KEY` provided)

---

## ⚙️ Flow Overview

1. Browser records with `MediaRecorder(audio/webm;codecs=opus)`  
2. Upload to `/scripts/chat(_stream)` → STT (`gpt-4o-mini-transcribe`)  
3. Query embedding → Redis cache → TourAPI if cache miss  
4. Generate TTS with `gpt-4o-mini-tts` → Base64 audio  
5. Live2D model plays audio with **ParamMouthOpenY** updates  
6. User can accept → `/scripts/courses` provides itineraries with narration  

---

## 🔐 Notes

- Avoid exposing keys directly in production. Use proxies or tokenization.  
- Image validation ensures safe links (`data_service.py`).  
- Sanitizer only allows `<a>` and `<br>`.  

---

## 📝 License & Credits

- Live2D assets follow their original license.  
- TourAPI: Korea Tourism Organization usage terms.  
- OpenAI: Service terms apply.  
