document.addEventListener('DOMContentLoaded', () => {
    // 카드에 호버 효과 추가
    const cards = document.querySelectorAll('.card');

    cards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-10px)';
            card.style.transition = 'transform 0.3s ease';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });

    // 페이지 로드 시 페이드인 효과
    document.querySelector('.main-container').style.opacity = '0';
    setTimeout(() => {
        document.querySelector('.main-container').style.opacity = '1';
        document.querySelector('.main-container').style.transition = 'opacity 0.5s ease';
    }, 100);

    const modal = document.getElementById('apiKeyModal');
    const setApiKeyBtn = document.getElementById('setApiKeyBtn');
    const closeModal = document.getElementById('closeModal');
    const saveApiKey = document.getElementById('saveApiKey');
    const openaiKeyInput = document.getElementById('openaiKeyInput');
    const tourKeyInput = document.getElementById('tourKeyInput');

    // API 키 저장/불러오기 함수들
    function getSavedOpenAIKey() {
        return localStorage.getItem('openai_api_key');
    }
    function getSavedTourKey() {
        return localStorage.getItem('tour_api_key');
    }
    function setSavedOpenAIKey(key) {
        localStorage.setItem('openai_api_key', key);
    }
    function setSavedTourKey(key) {
        localStorage.setItem('tour_api_key', key);
    }

    let savedOpenAIKey = getSavedOpenAIKey();
    let savedTourKey = getSavedTourKey();

    // 버튼 텍스트 업데이트
    function updateButtonText() {
        if (savedOpenAIKey && savedTourKey) {
            setApiKeyBtn.textContent = 'API 키 변경';
        } else {
            setApiKeyBtn.textContent = 'API 키 설정';
        }
    }
    updateButtonText();

    // 페이지 진입 시 API 키 확인
    function checkApiKeys() {
        return savedOpenAIKey && savedTourKey;
    }

    if (!checkApiKeys()) {
        modal.style.display = 'block';
    }

    // 모달 열기
    setApiKeyBtn.addEventListener('click', function() {
        modal.style.display = 'block';

        // 기존 값 표시
        if (getSavedOpenAIKey()) {
            openaiKeyInput.value = getSavedOpenAIKey();
        } else {
            openaiKeyInput.value = '';
        }

        if (getSavedTourKey()) {
            tourKeyInput.value = getSavedTourKey();
        } else {
            tourKeyInput.value = '';
        }
    });

    // 모달 닫기
    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    // API 키 저장
    saveApiKey.addEventListener('click', function() {
        const openaiKey = openaiKeyInput.value.trim();
        const tourKey = tourKeyInput.value.trim();

        let hasError = false;

        if (!openaiKey || !openaiKey.startsWith('sk-')) {
            alert('올바른 OpenAI API 키를 입력해주세요. (sk-로 시작해야 합니다)');
            hasError = true;
        }

        if (!tourKey) {
            alert('한국관광공사 TourAPI 키를 입력해주세요.');
            hasError = true;
        }

        if (!hasError) {
            setSavedOpenAIKey(openaiKey);
            setSavedTourKey(tourKey);
            savedOpenAIKey = openaiKey;
            savedTourKey = tourKey;
            updateButtonText();
            modal.style.display = 'none';
            alert('API 키가 성공적으로 저장되었습니다!');
        }
    });

    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // 캐릭터 선택 시 API 키 확인
    const characterLinks = document.querySelectorAll('.card:not(.disabled)');
    characterLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            if (!checkApiKeys()) {
                event.preventDefault();
                alert('대화를 시작하기 전에 API 키를 모두 설정해주세요.');
                modal.style.display = 'block';
            }
        });
    });
});