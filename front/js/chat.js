// // Live2D 모델 관리 클래스
// class Live2DManager {
//     constructor() {
//         this.model = null;
//         this.app = null;
//         this.canvas = document.getElementById('live2d-canvas');
//         window.PIXI = PIXI;
//         console.log('Live2DManager initialized');
//     }

//     async initialize() {
//         try {
//             this.app = new PIXI.Application({
//                 view: this.canvas,
//                 transparent: true,
//                 autoStart: true,
//                 resolution: window.devicePixelRatio || 1,
//                 antialias: true,
//                 autoDensity: true,
//                 backgroundColor: 0xffffff,
//                 backgroundAlpha: 0
//             });
//             console.log('PIXI Application created successfully');

//             const modelPath = '/model/kei/kei_vowels_pro.model3.json';
//             console.log('Loading Live2D model from:', modelPath);
//             this.model = await PIXI.live2d.Live2DModel.from(modelPath);
//             console.log('Live2D model loaded successfully');

//             this.model.scale.set(0.5);
//             this.model.anchor.set(0.5, 0.5);
//             this.model.x = this.app.screen.width / 2;
//             this.model.y = this.app.screen.height / 2;

//             this.app.stage.addChild(this.model);
//             this.setExpression('neutral');
//         } catch (error) {
//             console.error('Live2D model loading failed:', error);
//         }
//     }

//     setExpression(expression) {
//         if (this.model) {
//             try {
//                 console.log('Setting expression to:', expression);
//                 this.model.expression(expression);
//             } catch (error) {
//                 console.error('Failed to update Live2D expression:', error);
//             }
//         }
//     }

//     async playAudioWithLipSync(audioBase64) {
//         if (!this.model) {
//             console.warn('Live2D model not initialized');
//             return;
//         }

//         try {
//             console.log('Starting audio playback with lip sync');
//             const audioData = atob(audioBase64);
//             const arrayBuffer = new ArrayBuffer(audioData.length);
//             const uint8Array = new Uint8Array(arrayBuffer);
//             for (let i = 0; i < audioData.length; i++) {
//                 uint8Array[i] = audioData.charCodeAt(i);
//             }

//             let mimeType = 'audio/webm;codecs=opus';
//             if (!MediaRecorder.isTypeSupported(mimeType)) {
//                 alert('이 브라우저는 webm 녹음을 지원하지 않습니다. 최신 Chrome을 사용해 주세요.');
//                 return;
//             }
//             const audioBlob = new Blob([arrayBuffer], { type: mimeType });
//             const audioUrl = URL.createObjectURL(audioBlob);
//             console.log('Audio blob created and URL generated');

//             this.model.speak(audioUrl, {
//                 volume: 1.0,
//                 crossOrigin: 'anonymous'
//             });

//             return new Promise((resolve) => {
//                 setTimeout(() => {
//                     URL.revokeObjectURL(audioUrl);
//                     console.log('Audio playback completed, URL revoked');
//                     resolve();
//                 }, 500);
//             });
//         } catch (error) {
//             console.error('Audio playback error:', error);
//             this.setExpression('neutral');
//         }
//     }

//     stopSpeaking() {
//         if (this.model) {
//             console.log('Stopping speech and resetting expression');
//             this.model.stopSpeaking();
//             this.setExpression('neutral');
//         }
//     }

//     updateLipSync(volume) {
//         if (this.model && this.model.internalModel && this.model.internalModel.coreModel) {
//             this.model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', volume);
//         }
//     }
// }

// // 오디오 녹음 및 업로드 관리 클래스
// class AudioManager {
//     constructor() {
//         this.mediaRecorder = null;
//         this.audioChunks = [];
//         this.isRecording = false;
//         this.audioContext = null;
//         this.analyser = null;
//         this.processor = null;
//         this.audioStream = null;
//         this.initAudioContext();
//         console.log('AudioManager initialized');
//     }

//     initAudioContext() {
//         try {
//             this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
//             this.analyser = this.audioContext.createAnalyser();
//             console.log('Audio context initialized successfully');
//         } catch (error) {
//             console.error('Failed to initialize audio context:', error);
//         }
//     }

//     async startRecording() {
//         try {
//             if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
//                 throw new Error('Media Devices API not supported');
//             }
//             const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 24000 }, video: false });
//             console.log('Audio stream obtained successfully');

//             this.audioStream = stream;
//             let mimeType = 'audio/webm;codecs=opus';
//             if (!MediaRecorder.isTypeSupported(mimeType)) {
//                 alert('이 브라우저는 webm 녹음을 지원하지 않습니다. 최신 Chrome을 사용해 주세요.');
//                 return false;
//             }
//             this.mediaRecorder = new MediaRecorder(stream, { mimeType });

//             this.audioChunks = [];
//             this.mediaRecorder.ondataavailable = (event) => {
//                 if (event.data.size > 0) {
//                     this.audioChunks.push(event.data);
//                     console.log('Audio chunk received:', event.data.size, 'bytes', 'type:', event.data.type);
//                 }
//             };

//             if (this.audioContext && this.analyser) {
//                 const source = this.audioContext.createMediaStreamSource(stream);
//                 source.connect(this.analyser);
//                 console.log('Audio source connected to analyser');
//             }

//             this.mediaRecorder.start(100);
//             this.isRecording = true;
//             console.log('Recording started with format:', this.mediaRecorder.mimeType);
//             return true;
//         } catch (error) {
//             console.error('Failed to start recording:', error);
//             alert('마이크 접근 권한이 필요합니다. 브라우저 설정에서 마이크 권한을 허용해주세요.');
//             return false;
//         }
//     }

//     stopRecording() {
//         return new Promise((resolve) => {
//             if (this.mediaRecorder && this.isRecording) {
//                 console.log('Stopping recording');
//                 this.mediaRecorder.onstop = () => {
//                     const blob = this.getAudioBlob();
//                     this.audioChunks = [];
//                     this.isRecording = false;
//                     if (this.audioStream) {
//                         this.audioStream.getTracks().forEach(track => track.stop());
//                         this.audioStream = null;
//                     }
//                     resolve(blob);
//                 };
//                 this.mediaRecorder.stop();
//             } else {
//                 resolve(null);
//             }
//         });
//     }

//     getAudioBlob() {
//         if (this.mediaRecorder && this.mediaRecorder.mimeType.startsWith('audio/webm')) {
//             const blob = new Blob(this.audioChunks, { type: this.mediaRecorder.mimeType });
//             console.log('Audio blob created:', blob.size, 'bytes');
//             return blob;
//         } else {
//             alert('이 브라우저에서는 webm 녹음이 지원되지 않습니다. 최신 Chrome을 사용해 주세요.');
//             return null;
//         }
//     }

//     getAudioData() {
//         if (!this.analyser) {
//             console.warn('Analyser not initialized');
//             return new Uint8Array();
//         }
//         const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
//         this.analyser.getByteTimeDomainData(dataArray);
//         return dataArray;
//     }
// }

// // 채팅 및 대화 이력 관리 클래스
// class ChatManager {
//     constructor(characterType = 'kei') {
//         this.chatHistory = document.getElementById('chatHistory');
//         this.isPlaying = false;
//         this.conversationHistory = [];
//         this.characterType = characterType;
//         console.log('ChatManager initialized');
//     }

//     /**
//      * @param {'user'|'ai'|'system'} role
//      * @param {string} message
//      * @param {string|null} link  클릭 가능한 링크 (옵셔널)
//      * @param {object|null} aiPayload  전체 페이로드(프로액티브 카드 포함)
//      */
//     addMessage(role, message, link = null, aiPayload = null) {
//         console.log(`Adding ${role} message:`, message);
//         const messageElement = document.createElement('div');
//         messageElement.className = `message ${role}-message`;

//         if (role === 'ai') {
//             const profile = document.createElement('div');
//             profile.className = 'message-profile';
//             const characterImg = document.createElement('img');
//             characterImg.src = (
//                 this.characterType === 'haru' ? '/model/haru/profile.jpg' :
//                 this.characterType === 'kei' ? '/model/kei/profile.jpg' :
//                 '/model/momose/profile.jpg'
//             );
//             profile.appendChild(characterImg);
//             messageElement.appendChild(profile);
//         }

//         const messageBubble = document.createElement('div');
//         messageBubble.className = 'message-bubble';

//         const content = document.createElement('div');
//         content.className = 'message-content';
//         if (role === 'ai') {
//             const safeHTML = _sanitizeHtml(message);
//             content.innerHTML = safeHTML;
//             // 관광지 추천 카드가 있으면 HTML로 덧붙이기
//             if (aiPayload?.tour_recommendations) {
//                 const cardsHTML = _renderTourCards(aiPayload.tour_recommendations);
//                 if (cardsHTML) content.insertAdjacentHTML('beforeend', cardsHTML);
//             }
//         } else {
//             content.textContent = message;
//         }
//         messageBubble.appendChild(content);

//         // (호환) 링크 문자열이 별도로 넘어오면 기존 방식 유지
//         if (role === 'ai' && link) {
//             const linkWrap = document.createElement('div');
//             linkWrap.className = 'message-link';
//             const a = document.createElement('a');
//             a.href = link;
//             a.target = '_blank';
//             a.textContent = '▶️ 제안 링크 보기';
//             linkWrap.appendChild(a);
//             messageElement.appendChild(linkWrap);
//         }

//         const time = document.createElement('span');
//         time.className = 'message-time';
//         time.textContent = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });

//         messageBubble.appendChild(time);
//         messageElement.appendChild(messageBubble);
//         this.chatHistory.appendChild(messageElement);
//         this.chatHistory.scrollTop = this.chatHistory.scrollHeight;

//         this.conversationHistory.push({ role: role === 'user' ? 'user' : 'assistant', content: message });
//     }

//     async sendAudioToServer(audioBlob) {
//         try {
//             console.log('Preparing to send audio to server');
//             const formData = new FormData();
//             formData.append('audio', audioBlob, 'audio.webm');
//             formData.append('character', this.characterType);

//             const openaiKey = localStorage.getItem('openai_api_key');
//             const tourKey = localStorage.getItem('tour_api_key');
//             console.log('Sending request to server (once)');
//             const response = await fetch('/scripts/chat', {
//                 method: 'POST',
//                 body: formData,
//                 headers: {
//                     'X-API-KEY': openaiKey || '',
//                     'X-TOUR-API-KEY': tourKey || ''
//                 }
//             });

//             if (!response.ok) {
//                 const errorText = await response.text();
//                 console.error('Server error response:', errorText);
//                 throw new Error(`Server responded with ${response.status}: ${errorText}`);
//             }

//             const data = await response.json();
//             console.log('Server response received (once):', data);
//             return data;
//         } catch (error) {
//             console.error('Server communication error:', error);
//             throw error;
//         }
//     }

//     // 대화 기록 가져오기
//     getConversationHistory() {
//         return this.conversationHistory;
//     }
// }

// let live2dManager;  // Live2D 관리자 전역 변수
// let audioManager;   // 오디오 관리자 전역 변수
// let chatManager;    // 채팅 관리자 전역 변수

// // [NEW] 첫 응답 제어용 상태 & 간단 음성합성
// let lastRegion = "";
// let firstAiReplied = false;
// function speakInterim(text) {
//   try {
//     const u = new SpeechSynthesisUtterance(text);
//     u.lang = 'ko-KR';
//     window.speechSynthesis.cancel();
//     window.speechSynthesis.speak(u);
//   } catch(e){ console.warn('speechSynthesis not available:', e); }
// }

// // 립싱크 업데이트 함수
// function updateLipSync() {
//     if (audioManager && audioManager.isRecording) {
//         const audioData = audioManager.getAudioData();
//         let sum = 0;
//         for (let i = 0; i < audioData.length; i++) {
//             sum += Math.abs(audioData[i] - 128);
//         }
//         const average = sum / audioData.length;
//         const normalizedValue = average / 128;
//         live2dManager.updateLipSync(normalizedValue);
//     }
// }

// document.addEventListener('DOMContentLoaded', async () => {
//     console.log('Initializing application...');
//     live2dManager = new Live2DManager();
//     audioManager = new AudioManager();

//     // URL에서 캐릭터 타입 감지
//     const currentCharacter = window.location.pathname.includes('haru') ? 'haru' : 'kei';
//     chatManager = new ChatManager(currentCharacter);

//     await live2dManager.initialize();

//     // 캐릭터 로드 후 0.7초 뒤 안내 멘트
//     setTimeout(() => {
//         const greetingMessage = currentCharacter === 'haru'
//             ? '안녕하세요! 저는 여행 컨설턴트 Haru입니다. 한국의 관광지에 대해 궁금한 것이 있으면 언제든 물어보세요!'
//             : '안녕! 나는 Kei야! 한국 여행에 관해 뭐든 물어봐~ 맛집, 관광지, 숙소 다 알려줄게!';
//         chatManager.addMessage('ai', greetingMessage);
//     }, 700);

//     const recordButton = document.getElementById('recordButton');
//     recordButton.addEventListener('click', handleRecording);

//     setInterval(updateLipSync, 50);
//     console.log('Application initialization completed');
// });

// // 예/아니오 버튼
// function renderYesNoButtons(onYes, onNo) {
//   const wrap = document.createElement('div');
//   wrap.style.display = 'flex';
//   wrap.style.gap = '8px';
//   wrap.style.marginTop = '10px';

//   const yesBtn = document.createElement('button');
//   yesBtn.textContent = '예';
//   yesBtn.style.padding = '6px 12px';
//   yesBtn.style.borderRadius = '8px';
//   yesBtn.style.border = '1px solid #ddd';
//   yesBtn.style.cursor = 'pointer';
//   yesBtn.onclick = onYes;

//   const noBtn = document.createElement('button');
//   noBtn.textContent = '아니요';
//   noBtn.style.padding = '6px 12px';
//   noBtn.style.borderRadius = '8px';
//   noBtn.style.border = '1px solid #ddd';
//   noBtn.style.cursor = 'pointer';
//   noBtn.onclick = onNo;

//   wrap.appendChild(yesBtn);
//   wrap.appendChild(noBtn);
//   return wrap;
// }

// // 코스 카드 렌더
// function renderCourseCards(courses, regionLabel) {
//   if (!Array.isArray(courses) || courses.length === 0) return "";

//   const header = `<div class="tour-card-description" style="margin:6px 0 10px 0;">
//     간략한 추천 관광 코스는 <b>${_esc(regionLabel)}</b> 코스가 있으니 아래 내용을 확인해줘
//   </div>`;

//   const body = courses.map(c => {
//     const title = _esc(c.title || "코스");
//     const img   = c.thumbnail || "";
//     const link  = c.link || "";
//     const desc  = _esc(c.desc || "");
//     return `
//       <div class="tour-card">
//         <div class="tour-card-content">
//           ${img ? `<div class="tour-card-image"><img src="${img}" alt="${title}" onerror="this.style.display='none'"></div>` : ""}
//           <div class="tour-card-info">
//             <div class="tour-card-title">${title}</div>
//             ${desc ? `<div class="tour-card-description">${desc}</div>` : ""}
//             ${link ? `<div class="tour-card-link"><a href="${link}" target="_blank" rel="noopener">🔗 코스 상세 보기</a></div>` : ""}
//           </div>
//         </div>
//       </div>
//     `;
//   }).join("");

//   return `<div class="tour-cards-container">${header}${body}</div>`;
// }

// // 녹음 버튼 클릭 시 동작
// async function handleRecording() {
//     const recordButton = document.getElementById('recordButton');

//     if (chatManager.isPlaying) {
//         console.log('Cannot start recording while audio is playing');
//         return;
//     }

//     if (!audioManager.isRecording) {
//         console.log('Starting new recording');
//         const started = await audioManager.startRecording();
//         if (started) {
//             recordButton.textContent = '멈추기';
//             recordButton.classList.add('recording');
//             live2dManager.setExpression('listening');
//         }
//     } else {
//         console.log('Stopping recording and processing audio');
//         recordButton.disabled = true;
//         recordButton.textContent = '처리 중...';
//         recordButton.classList.remove('recording');
//         live2dManager.setExpression('neutral');

//         try {
//             const audioBlob = await audioManager.stopRecording();
//             if (!audioBlob) throw new Error('No audio data recorded');

//             // [NEW] 사용자 임시 말풍선(곧 STT 결과로 대체)
//             const pendingUserEl = document.createElement('div');
//             pendingUserEl.className = 'message user-message';
//             pendingUserEl.innerHTML = `
//               <div class="message-bubble">
//                 <div class="message-content">… (음성 인식 중)</div>
//                 <span class="message-time">${new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}</span>
//               </div>`;
//             chatManager.chatHistory.appendChild(pendingUserEl);
//             chatManager.chatHistory.scrollTop = chatManager.chatHistory.scrollHeight;

//             // [NEW] 중간 멘트(텍스트+음성)로 시간 벌기
//             const interim1 = "~ 정보를 알려달라는 거지!";
//             chatManager.addMessage('ai', interim1);
//             speakInterim(interim1);

//             const interim2 = "찾고 있으니까 조금만 기다려줘";
//             chatManager.addMessage('ai', interim2);
//             speakInterim(interim2);

//             console.log('Sending audio to server for processing');
//             let response;
//             try {
//                 response = await sendAudioToServerStream(audioBlob, chatManager.characterType);
//             } catch (e) {
//                 console.warn('stream failed, fallback to once:', e);
//                 response = await chatManager.sendAudioToServer(audioBlob);
//             }

//             // STT 결과로 임시 사용자 말풍선 대체
//             if (response.user_text) {
//                 const contentEl = pendingUserEl.querySelector('.message-content');
//                 if (contentEl) contentEl.textContent = response.user_text;
//             }

//             if (response.ai_text) {
//                 // AI 본문 + (있다면) 관광지 카드
//                 chatManager.addMessage('ai', response.ai_text, null, response);

//                 // 첫 AI 응답에 지역 저장 + 버튼 배치
//                 if (!firstAiReplied && Array.isArray(response.tour_recommendations) && response.tour_recommendations.length > 0) {
//                     const metaRegion = response.tour_recommendations[0]?.metadata?.region || "";
//                     if (metaRegion) lastRegion = metaRegion;

//                     const lastMsg = chatManager.chatHistory.lastElementChild;
//                     const mount = lastMsg?.querySelector('.message-bubble');
//                     if (mount) {
//                         const row = renderYesNoButtons(async () => {
//                             // 예: 코스 3개 불러오기
//                             try {
//                                 chatManager.addMessage('user', '예');
//                                 const res = await fetch(`/scripts/courses?region=${encodeURIComponent(lastRegion)}&n=3`);
//                                 const j = await res.json();
//                                 const cardsHTML = renderCourseCards(j.courses || [], lastRegion || '지역');

//                                 // 카드가 깨지지 않도록: 먼저 빈 AI 말풍선 추가 후 그 안에 직접 삽입
//                                 chatManager.addMessage('ai', '간략한 추천 관광 코스를 정리했어!');
//                                 const aiLast = chatManager.chatHistory.lastElementChild;
//                                 const mc = aiLast?.querySelector('.message-content');
//                                 if (mc && cardsHTML) {
//                                   mc.insertAdjacentHTML('beforeend', cardsHTML);
//                                 }
//                             } catch (err) {
//                                 console.error(err);
//                                 chatManager.addMessage('system', '코스 정보를 불러오지 못했어요.');
//                             }
//                             row.remove();
//                         }, () => {
//                             chatManager.addMessage('user', 'अ니요'); // 오타 방지: '아니요'
//                             row.remove();
//                         });
//                         mount.appendChild(row);
//                     }
//                     firstAiReplied = true;
//                 }

//                 if (response.audio) {
//                     console.log('Starting audio playback');
//                     chatManager.isPlaying = true;
//                     live2dManager.setExpression('speaking');

//                     try {
//                         await live2dManager.playAudioWithLipSync(response.audio);
//                         console.log('Audio playback completed');
//                     } catch (error) {
//                         console.error('Playback error:', error);
//                     } finally {
//                         live2dManager.setExpression('neutral');
//                         chatManager.isPlaying = false;
//                     }
//                 }
//             }
//         } catch (error) {
//             console.error('Error processing recording:', error);
//             chatManager.addMessage('system', '오류가 발생했습니다. 다시 시도해주세요.');
//         } finally {
//             live2dManager.setExpression('neutral');
//             chatManager.isPlaying = false;
//             recordButton.disabled = false;
//             recordButton.textContent = '이야기하기';
//         }
//     }
// }

// // ====== 스트리밍 송수신: /scripts/chat_stream ======
// async function sendAudioToServerStream(audioBlob, characterType = 'kei') {
//   const openaiKey = localStorage.getItem('openai_api_key') || '';
//   const tourKey = localStorage.getItem('tour_api_key') || '';
//   const formData = new FormData();
//   formData.append('audio', audioBlob, 'audio.webm');
//   formData.append('character', characterType);

//   const resp = await fetch('/scripts/chat_stream', {
//     method: 'POST',
//     headers: {
//       'X-API-KEY': openaiKey,
//       'X-TOUR-API-KEY': tourKey
//     },
//     body: formData
//   });

//   if (!resp.ok || !resp.body) {
//     throw new Error(`stream failed: ${resp.status}`);
//   }

//   const reader = resp.body.getReader();
//   const decoder = new TextDecoder('utf-8');
//   let buffer = '';
//   let finalPayload = null;

//   // 최초 토큰 수신 시 AI 말풍선 뼈대
//   let hasSkeleton = false;
//   let skeletonEl = null;

//   while (true) {
//     const { value, done } = await reader.read();
//     if (done) break;
//     buffer += decoder.decode(value, { stream: true });

//     let idx;
//     while ((idx = buffer.indexOf('\n\n')) >= 0) {
//       const chunk = buffer.slice(0, idx).trim();
//       buffer = buffer.slice(idx + 2);

//       // SSE 포맷: "event: token" + "data: {...}"
//       const lines = chunk.split('\n');
//       const ev = (lines.find(l => l.startsWith('event:')) || '').slice(6).trim();
//       const dataLine = (lines.find(l => l.startsWith('data:')) || '').slice(5).trim();

//       if (!ev || !dataLine) continue;

//       if (ev === 'token') {
//         const { token } = JSON.parse(dataLine);
//         if (!hasSkeleton) {
//           chatManager.addMessage('ai', '', null, null);
//           skeletonEl = chatManager.chatHistory.lastElementChild.querySelector('.message-content');
//           hasSkeleton = true;
//         }
//         if (skeletonEl) {
//           const safe = _sanitizeHtml((skeletonEl.innerHTML || '') + token);
//           skeletonEl.innerHTML = safe;
//           chatManager.chatHistory.scrollTop = chatManager.chatHistory.scrollHeight;
//         }
//       } else if (ev === 'final') {
//         finalPayload = JSON.parse(dataLine);
//       }
//     }
//   }

//   if (!finalPayload) throw new Error('no final payload from stream');
//   return finalPayload;
// }

// // [ADD] 안전한 HTML 이스케이프
// function _esc(s){return (s||"").replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}

// // [MOD] 제안 카드 HTML (홈페이지 링크 노출, reason 폴백 추가)
// function _renderTourCards(recommendations){
//   if(!recommendations || !Array.isArray(recommendations) || recommendations.length === 0) return "";

//   const cardsHTML = recommendations.map(place => {
//     const name = _esc(place.name || "이름 정보 없음");
//     const reason = _esc(place.reason || "설명 없음");
//     const address = _esc(place.address || "주소 정보 없음");
//     const imageUrl = place.image_url || "";
//     const homepage = place.homepage || "";

//     return `
//       <div class="tour-card">
//         <div class="tour-card-content">
//           ${imageUrl ? `
//             <div class="tour-card-image">
//               <img src="${imageUrl}" alt="${name}" onerror="this.style.display='none'">
//             </div>` : ""}
//           <div class="tour-card-info">
//             <div class="tour-card-title">${name}</div>
//             <div class="tour-card-description">${reason}</div>
//             <div class="tour-card-address">📍 ${address}</div>
//             ${homepage ? `<div class="tour-card-link"><a href="${homepage}" target="_blank" rel="noopener">🔗 홈페이지 보기</a></div>` : ""}
//           </div>
//         </div>
//       </div>`;
//   }).join("");

//   return `<div class="tour-cards-container">${cardsHTML}</div>`;
// }

// // [ADD] 허용 태그만 남기는 간단 Sanitizer: <a>, <br>만 허용
// function _sanitizeHtml(input) {
//   const wrapper = document.createElement('div');
//   wrapper.innerHTML = input || '';

//   const allowed = new Set(['A', 'BR']);

//   const all = wrapper.querySelectorAll('*');
//   for (const el of all) {
//     const tag = el.tagName;
//     if (!allowed.has(tag)) {
//       el.replaceWith(document.createTextNode(el.textContent || ''));
//       continue;
//     }
//     if (tag === 'A') {
//       const href = el.getAttribute('href') || '';
//       if (!/^https?:\/\//i.test(href)) {
//         el.replaceWith(document.createTextNode(el.textContent || ''));
//         continue;
//       }
//       el.setAttribute('target', '_blank');
//       el.setAttribute('rel', 'noopener noreferrer');
//       for (const attr of [...el.attributes]) {
//         const name = attr.name.toLowerCase();
//         if (!['href', 'target', 'rel'].includes(name)) el.removeAttribute(attr.name);
//       }
//     }
//   }
//   return wrapper.innerHTML.replace(/\n/g, '<br>');
// }

// Live2D 모델 관리 클래스
class Live2DManager {
  constructor(){
    this.model=null; this.app=null; this.canvas=document.getElementById('live2d-canvas');
    window.PIXI=PIXI;
  }
  async initialize(){
    try{
      this.app=new PIXI.Application({view:this.canvas,transparent:true,autoStart:true,resolution:window.devicePixelRatio||1,antialias:true,autoDensity:true,backgroundAlpha:0});
      const modelPath='/model/kei/kei_vowels_pro.model3.json';
      this.model=await PIXI.live2d.Live2DModel.from(modelPath);
      this.model.scale.set(0.5); this.model.anchor.set(0.5,0.5);
      this.model.x=this.app.screen.width/2; this.model.y=this.app.screen.height/2;
      this.app.stage.addChild(this.model); this.setExpression('neutral');
    }catch(e){ console.error(e); }
  }
  setExpression(exp){ try{ this.model?.expression(exp);}catch(e){} }
  async playAudioWithLipSync(audioBase64){
    if(!this.model) return;
    try{
      const bin=atob(audioBase64); const buf=new ArrayBuffer(bin.length); const u8=new Uint8Array(buf);
      for(let i=0;i<bin.length;i++) u8[i]=bin.charCodeAt(i);
      const blob=new Blob([buf],{type:'audio/webm;codecs=opus'}); const url=URL.createObjectURL(blob);
      this.model.speak(url,{volume:1.0,crossOrigin:'anonymous'}); setTimeout(()=>URL.revokeObjectURL(url),500);
    }catch(e){ console.error(e); this.setExpression('neutral'); }
  }
  stopSpeaking(){ try{ this.model?.stopSpeaking(); this.setExpression('neutral'); }catch(e){} }
  updateLipSync(v){ try{ this.model?.internalModel?.coreModel?.setParameterValueById('ParamMouthOpenY',v);}catch(e){} }
}

// 오디오 녹음
class AudioManager{
  constructor(){
    this.mediaRecorder=null; this.audioChunks=[]; this.isRecording=false;
    this.audioContext=null; this.analyser=null; this.audioStream=null;
    this.initAudioContext();
  }
  initAudioContext(){
    try{ this.audioContext=new (window.AudioContext||window.webkitAudioContext)(); this.analyser=this.audioContext.createAnalyser(); }catch(e){console.error(e);}
  }
  async startRecording(){
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,sampleRate:24000},video:false});
      this.audioStream=stream;
      const mimeType='audio/webm;codecs=opus';
      if(!MediaRecorder.isTypeSupported(mimeType)){ alert('webm 녹음을 지원하지 않습니다.'); return false; }
      this.mediaRecorder=new MediaRecorder(stream,{mimeType});
      this.audioChunks=[]; this.mediaRecorder.ondataavailable=(e)=>{ if(e.data.size>0) this.audioChunks.push(e.data); };
      this.mediaRecorder.start(100);
      if(this.audioContext&&this.analyser){ const src=this.audioContext.createMediaStreamSource(stream); src.connect(this.analyser); }
      this.isRecording=true; return true;
    }catch(e){ alert('마이크 권한이 필요합니다.'); return false; }
  }
  stopRecording(){
    return new Promise((resolve)=>{
      if(this.mediaRecorder&&this.isRecording){
        this.mediaRecorder.onstop=()=>{
          const blob=new Blob(this.audioChunks,{type:this.mediaRecorder.mimeType});
          this.audioChunks=[]; this.isRecording=false;
          this.audioStream?.getTracks().forEach(t=>t.stop()); this.audioStream=null;
          resolve(blob);
        };
        this.mediaRecorder.stop();
      }else resolve(null);
    });
  }
  getAudioData(){
    if(!this.analyser) return new Uint8Array();
    const arr=new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteTimeDomainData(arr); return arr;
  }
}

// 채팅
class ChatManager{
  constructor(characterType='kei'){
    this.chatHistory=document.getElementById('chatHistory');
    this.isPlaying=false; this.conversationHistory=[]; this.characterType=characterType;
  }
  addMessage(role,message,link=null,aiPayload=null){
    const el=document.createElement('div'); el.className=`message ${role}-message`;
    if(role==='ai'){
      const profile=document.createElement('div'); profile.className='message-profile';
      const img=document.createElement('img');
      img.src=(this.characterType==='haru'?'/model/haru/profile.jpg':'/model/kei/profile.jpg');
      profile.appendChild(img); el.appendChild(profile);
    }
    const bubble=document.createElement('div'); bubble.className='message-bubble';
    const content=document.createElement('div'); content.className='message-content';
    if(role==='ai'){
      content.innerHTML=_sanitizeHtml(message);
      if(aiPayload?.tour_recommendations){
        const html=_renderTourCards(aiPayload.tour_recommendations);
        if(html) content.insertAdjacentHTML('beforeend', html);
      }
    }else{ content.textContent=message; }
    bubble.appendChild(content);
    const time=document.createElement('span'); time.className='message-time';
    time.textContent=new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'});
    bubble.appendChild(time); el.appendChild(bubble);
    this.chatHistory.appendChild(el);
    this.chatHistory.scrollTop=this.chatHistory.scrollHeight;
    this.conversationHistory.push({role:role==='user'?'user':'assistant', content:message});
  }
  async sendAudioToServer(blob){
    const form=new FormData(); form.append('audio',blob,'audio.webm'); form.append('character',this.characterType);
    const openaiKey=localStorage.getItem('openai_api_key')||''; const tourKey=localStorage.getItem('tour_api_key')||'';
    const res=await fetch('/scripts/chat',{method:'POST',body:form,headers:{'X-API-KEY':openaiKey,'X-TOUR-API-KEY':tourKey}});
    if(!res.ok) throw new Error(await res.text()); return await res.json();
  }
  getConversationHistory(){ return this.conversationHistory; }
}

let live2dManager,audioManager,chatManager;
let lastRegion=""; let firstAiReplied=false;

// 간단 TTS
function speakInterim(text){
  try{ const u=new SpeechSynthesisUtterance(text); u.lang='ko-KR'; window.speechSynthesis.cancel(); window.speechSynthesis.speak(u);}catch(e){}
}
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));

// 립싱크
function updateLipSync(){
  if(audioManager&&audioManager.isRecording){
    const d=audioManager.getAudioData(); let s=0; for(let i=0;i<d.length;i++) s+=Math.abs(d[i]-128);
    live2dManager.updateLipSync((s/d.length)/128);
  }
}

document.addEventListener('DOMContentLoaded', async ()=>{
  live2dManager=new Live2DManager(); audioManager=new AudioManager();
  const currentCharacter=window.location.pathname.includes('haru')?'haru':'kei';
  chatManager=new ChatManager(currentCharacter);
  await live2dManager.initialize();
  setTimeout(()=>{
    const msg=currentCharacter==='haru'
      ? '안녕하세요! 저는 여행 컨설턴트 Haru입니다. 한국의 관광지에 대해 궁금한 것이 있으면 언제든 물어보세요!'
      : '안녕! 나는 Kei야! 한국 여행에 관해 뭐든 물어봐~ 맛집, 관광지, 숙소 다 알려줄게!';
    chatManager.addMessage('ai', msg);
  },700);
  document.getElementById('recordButton').addEventListener('click', handleRecording);
  setInterval(updateLipSync,50);
});

// 예/아니오 버튼
function renderYesNoButtons(onYes,onNo){
  const wrap=document.createElement('div'); wrap.style.display='flex'; wrap.style.gap='8px'; wrap.style.marginTop='10px';
  const yes=document.createElement('button'); yes.textContent='예'; yes.style.padding='6px 12px'; yes.style.borderRadius='8px'; yes.style.border='1px solid #ddd'; yes.style.cursor='pointer'; yes.onclick=onYes;
  const no=document.createElement('button'); no.textContent='아니요'; no.style.padding='6px 12px'; no.style.borderRadius='8px'; no.style.border='1px solid #ddd'; no.style.cursor='pointer'; no.onclick=onNo;
  wrap.appendChild(yes); wrap.appendChild(no); return wrap;
}

// 코스 카드
function renderCourseCards(courses, regionLabel){
  if(!Array.isArray(courses)||courses.length===0) return "";
  const header=`<div class="tour-card-description" style="margin:6px 0 10px 0;">
    간략한 추천 관광 코스는 <b>${_esc(regionLabel)}</b> 코스가 있으니 아래 내용을 확인해줘
  </div>`;
  const body=courses.map(c=>{
    const title=_esc(c.title||"코스"); const img=c.thumbnail||""; const link=c.link||""; const desc=_esc(c.desc||"");
    return `<div class="tour-card">
      <div class="tour-card-content">
        ${img?`<div class="tour-card-image"><img src="${img}" alt="${title}" onerror="this.style.display='none'"></div>`:""}
        <div class="tour-card-info">
          <div class="tour-card-title">${title}</div>
          ${desc?`<div class="tour-card-description">${desc}</div>`:""}
          ${link?`<div class="tour-card-link"><a href="${link}" target="_blank" rel="noopener">🔗 코스 상세 보기</a></div>`:""}
        </div>
      </div>
    </div>`;
  }).join("");
  return `<div class="tour-cards-container">${header}${body}</div>`;
}

// 카테고리 라벨
const CAT1_NAME={A01:'자연',A02:'문화',A03:'레포츠',A04:'쇼핑',A05:'음식',B02:'숙박',C01:'추천코스'};

// 녹음 버튼
async function handleRecording(){
  const btn=document.getElementById('recordButton');
  if(chatManager.isPlaying) return;

  if(!audioManager.isRecording){
    const ok=await audioManager.startRecording();
    if(ok){ btn.textContent='멈추기'; btn.classList.add('recording'); live2dManager.setExpression('listening'); }
  }else{
    btn.disabled=true; btn.textContent='처리 중...'; btn.classList.remove('recording'); live2dManager.setExpression('neutral');
    try{
      const blob=await audioManager.stopRecording(); if(!blob) throw new Error('No audio');

      // 사용자 임시 버블
      const pending=document.createElement('div');
      pending.className='message user-message';
      pending.innerHTML=`<div class="message-bubble">
        <div class="message-content">… (음성 인식 중)</div>
        <span class="message-time">${new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}</span>
      </div>`;
      chatManager.chatHistory.appendChild(pending);
      chatManager.chatHistory.scrollTop=chatManager.chatHistory.scrollHeight;

      // 서버 전송(스트림 우선)
      let response;
      try{ response=await sendAudioToServerStream(blob, chatManager.characterType); }
      catch(e){ response=await chatManager.sendAudioToServer(blob); }

      // STT 결과 반영
      if(response.user_text){
        const c=pending.querySelector('.message-content'); if(c) c.textContent=response.user_text;
      }

      // 최종 답변/오디오
      if(response.ai_text){
        chatManager.addMessage('ai', response.ai_text, null, response);

        // 첫 응답 → 버튼/지역 저장
        if(!firstAiReplied && Array.isArray(response.tour_recommendations) && response.tour_recommendations.length>0){
          const metaRegion=response.tour_recommendations[0]?.metadata?.region||"";
          if(metaRegion) lastRegion=metaRegion;
          const lastMsg=chatManager.chatHistory.lastElementChild;
          const mount=lastMsg?.querySelector('.message-bubble');
          if(mount){
            const row=renderYesNoButtons(async ()=>{
              chatManager.addMessage('user','예');
              try{
                const res=await fetch(`/scripts/courses?region=${encodeURIComponent(lastRegion)}&n=3`);
                const j=await res.json();
                if(!j.courses || j.courses.length===0){
                  chatManager.addMessage('ai','해당 지역의 코스를 아직 못 찾았어. 다른 지역도 물어볼까?');
                }else{
                  const announce='간략한 추천 관광 코스를 정리했어! 아래 카드를 확인해줘';
                  chatManager.addMessage('ai', announce); speakInterim(announce);
                  const aiLast=chatManager.chatHistory.lastElementChild;
                  const mc=aiLast?.querySelector('.message-content');
                  const cardsHTML=renderCourseCards(j.courses, lastRegion||'지역');
                  if(mc && cardsHTML) mc.insertAdjacentHTML('beforeend', cardsHTML);
                }
              }catch(err){
                console.error(err); chatManager.addMessage('system','코스 정보를 불러오지 못했어요.');
              }
              row.remove();
            }, ()=>{ chatManager.addMessage('user','아니요'); row.remove(); });
            mount.appendChild(row);
          }
          firstAiReplied=true;
        }

        if(response.audio){
          chatManager.isPlaying=true; live2dManager.setExpression('speaking');
          try{ await live2dManager.playAudioWithLipSync(response.audio); }
          finally{ live2dManager.setExpression('neutral'); chatManager.isPlaying=false; }
        }
      }
    }catch(e){
      console.error(e); chatManager.addMessage('system','오류가 발생했습니다. 다시 시도해주세요.');
    }finally{
      live2dManager.setExpression('neutral'); chatManager.isPlaying=false; btn.disabled=false; btn.textContent='이야기하기';
    }
  }
}

// ====== 스트리밍 송수신: /scripts/chat_stream ======
async function sendAudioToServerStream(audioBlob, characterType='kei'){
  const openaiKey=localStorage.getItem('openai_api_key')||'';
  const tourKey=localStorage.getItem('tour_api_key')||'';
  const formData=new FormData();
  formData.append('audio', audioBlob, 'audio.webm');
  formData.append('character', characterType);

  const resp=await fetch('/scripts/chat_stream',{method:'POST',headers:{'X-API-KEY':openaiKey,'X-TOUR-API-KEY':tourKey},body:formData});
  if(!resp.ok || !resp.body) throw new Error(`stream failed: ${resp.status}`);

  const reader=resp.body.getReader(); const decoder=new TextDecoder('utf-8');
  let buffer=''; let finalPayload=null;

  // 중간 멘트 타이머 제어
  let interimScheduled=false;
  let interimTimer1=null, interimTimer2=null;
  let interimText1=''; // "<지역> <카테고리> 정보를 원하는거지?"
  const catLabel=(c)=>({A01:'자연',A02:'문화',A03:'레포츠',A04:'쇼핑',A05:'음식',B02:'숙박',C01:'추천코스'}[c]||'관광지');

  // 최초 토큰 수신 시 AI 버블 뼈대
  let hasSkeleton=false; let skeletonEl=null;

  while(true){
    const {value, done}=await reader.read(); if(done) break;
    buffer+=decoder.decode(value,{stream:true});

    let idx;
    while((idx=buffer.indexOf('\n\n'))>=0){
      const chunk=buffer.slice(0,idx).trim(); buffer=buffer.slice(idx+2);
      const lines=chunk.split('\n');
      const ev=(lines.find(l=>l.startsWith('event:'))||'').slice(6).trim();
      const dataLine=(lines.find(l=>l.startsWith('data:'))||'').slice(5).trim();
      if(!ev || !dataLine) continue;

      if(ev==='meta'){
        // region/cat1 힌트를 받으면 적당한 시간 간격으로 중간멘트 예약
        try{
          const meta=JSON.parse(dataLine);
          const region=(meta.region||'').trim();
          const cat=(meta.cat1||'').trim();
          interimText1 = region ? `${region} ${catLabel(cat)} 정보를 원하는거지?` : `${catLabel(cat)} 정보를 원하는거지?`;
          if(!interimScheduled){
            interimScheduled=true;
            interimTimer1=setTimeout(()=>{ chatManager.addMessage('ai', interimText1); speakInterim(interimText1); }, 600);
            interimTimer2=setTimeout(()=>{ const t='찾고 있으니까 조금만 기다려줘'; chatManager.addMessage('ai', t); speakInterim(t); }, 1500);
          }
        }catch(e){}
      }
      else if(ev==='token'){
        const {token}=JSON.parse(dataLine);
        if(!hasSkeleton){
          chatManager.addMessage('ai','',null,null);
          skeletonEl=chatManager.chatHistory.lastElementChild.querySelector('.message-content');
          hasSkeleton=true;
        }
        if(skeletonEl){
          const safe=_sanitizeHtml((skeletonEl.innerHTML||'')+token);
          skeletonEl.innerHTML=safe;
          chatManager.chatHistory.scrollTop=chatManager.chatHistory.scrollHeight;
        }
      }
      else if(ev==='final'){
        finalPayload=JSON.parse(dataLine);
        // 타이머 정리
        if(interimTimer1) clearTimeout(interimTimer1);
        if(interimTimer2) clearTimeout(interimTimer2);
      }
    }
  }

  if(!finalPayload) throw new Error('no final payload from stream');
  return finalPayload;
}

// Sanitizer & 카드 렌더
function _esc(s){return (s||"").replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function _renderTourCards(recommendations){
  if(!recommendations||!Array.isArray(recommendations)||recommendations.length===0) return "";
  const html=recommendations.map(p=>{
    const name=_esc(p.name||"이름 정보 없음");
    const reason=_esc(p.reason||"설명 없음");
    const address=_esc(p.address||"주소 정보 없음");
    const imageUrl=p.image_url||""; const homepage=p.homepage||"";
    return `<div class="tour-card">
      <div class="tour-card-content">
        ${imageUrl?`<div class="tour-card-image"><img src="${imageUrl}" alt="${name}" onerror="this.style.display='none'"></div>`:""}
        <div class="tour-card-info">
          <div class="tour-card-title">${name}</div>
          <div class="tour-card-description">${reason}</div>
          <div class="tour-card-address">📍 ${address}</div>
          ${homepage?`<div class="tour-card-link"><a href="${homepage}" target="_blank" rel="noopener">🔗 홈페이지 보기</a></div>`:""}
        </div>
      </div>
    </div>`;
  }).join("");
  return `<div class="tour-cards-container">${html}</div>`;
}
function _sanitizeHtml(input){
  const w=document.createElement('div'); w.innerHTML=input||'';
  const allowed=new Set(['A','BR']);
  const all=w.querySelectorAll('*');
  for(const el of all){
    const tag=el.tagName;
    if(!allowed.has(tag)){ el.replaceWith(document.createTextNode(el.textContent||'')); continue; }
    if(tag==='A'){
      const href=el.getAttribute('href')||'';
      if(!/^https?:\/\//i.test(href)){ el.replaceWith(document.createTextNode(el.textContent||'')); continue; }
      el.setAttribute('target','_blank'); el.setAttribute('rel','noopener noreferrer');
      for(const attr of [...el.attributes]){ const n=attr.name.toLowerCase(); if(!['href','target','rel'].includes(n)) el.removeAttribute(attr.name); }
    }
  }
  return w.innerHTML.replace(/\n/g,'<br>');
}
