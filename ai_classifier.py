import json
import os
import streamlit as st
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get_api_key() -> str:
    try:
        return st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """당신은 태스크 분류 전문가입니다. 사용자가 입력한 태스크의 제목과 설명을 분석하여 다음을 판단해주세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

{
    "category": "업무" 또는 "개인",
    "priority": "높음" 또는 "중간" 또는 "낮음",
    "urgency": "긴급" 또는 "보통" 또는 "여유",
    "quadrant": 1~4 중 숫자
}

분류 기준:
- category: 회사, 업무, 보고서, 회의, 프레젠테이션, 클라이언트 등 → "업무" / 운동, 장보기, 가족, 취미, 개인 약속 등 → "개인"
- priority: 비즈니스 임팩트, 결과의 중대성, 장기적 가치 기준
- urgency: 시간적 압박, 즉시 대응 필요 여부 기준

아이젠하워 매트릭스 사분면:
- 1: 긴급하고 중요함 (즉시 실행)
- 2: 긴급하지 않지만 중요함 (계획 수립)
- 3: 긴급하지만 중요하지 않음 (위임)
- 4: 긴급하지도 중요하지도 않음 (제거 고려)
"""


def classify_task(title: str, description: str = "") -> dict:
    """OpenAI GPT를 사용하여 태스크를 자동 분류합니다."""
    api_key = _get_api_key()
    if not api_key or api_key == "sk-없음":
        return _default_classification()

    client = OpenAI(api_key=api_key)

    user_msg = f"태스크 제목: {title}"
    if description:
        user_msg += f"\n설명: {description}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=200,
        )
        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        # 값 검증
        if result.get("category") not in ("업무", "개인"):
            result["category"] = "업무"
        if result.get("priority") not in ("높음", "중간", "낮음"):
            result["priority"] = "중간"
        if result.get("urgency") not in ("긴급", "보통", "여유"):
            result["urgency"] = "보통"
        if result.get("quadrant") not in (1, 2, 3, 4):
            result["quadrant"] = 4

        return result
    except Exception:
        return _default_classification()


def _default_classification() -> dict:
    return {
        "category": "업무",
        "priority": "중간",
        "urgency": "보통",
        "quadrant": 4,
    }
