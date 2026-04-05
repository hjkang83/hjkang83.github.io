"""Step 4: Gemini API 호출 모듈."""

import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud: st.secrets / 로컬: .env
try:
    import streamlit as st
    _API_KEY = st.secrets.get("GEMINI_API_KEY")
except Exception:
    _API_KEY = None

if not _API_KEY:
    _API_KEY = os.getenv("GEMINI_API_KEY")

if _API_KEY:
    genai.configure(api_key=_API_KEY)

MODEL_NAME = "gemini-2.5-flash"


def generate_explanation(image, prompt):
    """사진과 프롬프트를 Gemini에 보내고 설명 텍스트를 받는다.

    Args:
        image: PIL Image 객체
        prompt: 완성된 프롬프트 문자열

    Returns:
        AI가 생성한 설명 텍스트, 실패 시 에러 안내 메시지
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"⚠️ AI 설명 생성에 실패했습니다. 잠시 후 다시 시도해주세요.\n(오류: {e})"


def identify_place(image, place_names):
    """사진 속 건물/유적지를 Gemini로 인식하여 등록된 장소 중 매칭되는 것을 찾는다.

    Args:
        image: PIL Image 객체
        place_names: 등록된 장소 이름 리스트

    Returns:
        {"matched": "장소이름", "confidence": "높음/보통/낮음", "description": "인식 근거"}
        또는 인식 실패 시 None
    """
    place_list = "\n".join(f"- {name}" for name in place_names)
    prompt = (
        "이 사진에 보이는 건물이나 유적지를 분석해줘.\n\n"
        f"아래는 등록된 장소 목록이야:\n{place_list}\n\n"
        "위 목록 중에서 사진과 가장 일치하는 장소를 골라줘.\n"
        "반드시 아래 형식으로만 답해줘 (다른 말 하지 마):\n"
        "장소: [장소이름]\n"
        "확신도: [높음/보통/낮음]\n"
        "근거: [사진에서 어떤 특징을 보고 판단했는지 한 줄로]"
    )
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([prompt, image])
        text = response.text.strip()

        result = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("장소:"):
                result["matched"] = line.replace("장소:", "").strip()
            elif line.startswith("확신도:"):
                result["confidence"] = line.replace("확신도:", "").strip()
            elif line.startswith("근거:"):
                result["description"] = line.replace("근거:", "").strip()

        if "matched" in result and result["matched"] in place_names:
            return result
        return None
    except Exception:
        return None
