import re

def remove_empty_parentheses(text):
    return re.sub(r'\(\s*\)', '', text)

def remove_emojis(text):
    """
    이모지(Unicode 이모티콘) 및 일부 특수 아이콘을 모두 제거합니다.
    """
    emoji_pattern = re.compile(
        "["               
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\u2600-\u26FF"          # miscellaneous symbols
        "\u2700-\u27BF"          # dingbats
        "]",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text)

def prettify_message(text):
    text = remove_empty_parentheses(text)
    text = remove_emojis(text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'링크:\s*', '\n링크: ', text)
    return text.strip()

def markdown_to_html_links(text):
    return re.sub(r'\[([^\]])\]\((https?://[^\)])\)', r'<a href="\2" target="_blank">\1</a>', text)

def extract_first_markdown_url(text):
    match = re.search(r'\[([^\]])\]\((https?://[^\)])\)', text)
    if match:
        return match.group(2)
    return None 

# =========================
# Hangul 받침 유틸리티
# =========================
def _has_jongseong(ch: str) -> bool:
    """단일 한글 음절 ch에 받침(종성)이 있으면 True."""
    if not ch:
        return False
    code = ord(ch)
    # 가(AC00) ~ 힣(D7A3)
    if 0xAC00 <= code <= 0xD7A3:
        jong = (code - 0xAC00) % 28
        return jong != 0
    return False

def ends_with_batchim(text: str) -> bool:
    """
    문자열의 '마지막 한글 음절' 기준으로 받침 여부를 판단.
    공백/구두점/이모지 등은 건너뛰고, 한글이 없으면 False.
    """
    if not text:
        return False
    for ch in reversed(text.strip()):
        if '\uAC00' <= ch <= '\uD7A3':
            return _has_jongseong(ch)
    return False

def copula_iy_a(noun: str) -> str:
    """
    국어 규칙:
      - 받침 있는 명사 뒤: '이야'
      - 받침 없는 명사 뒤: '야'
    """
    return "이야" if ends_with_batchim(noun or "") else "야"