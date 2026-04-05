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
