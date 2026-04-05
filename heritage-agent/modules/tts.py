"""Step 5: 텍스트 → 음성 변환 모듈."""

from io import BytesIO

from gtts import gTTS


def text_to_speech(text):
    """텍스트를 한국어 음성(mp3)으로 변환한다.

    Args:
        text: 설명 텍스트 문자열

    Returns:
        mp3 바이너리 데이터가 담긴 BytesIO 객체
    """
    tts = gTTS(text=text, lang="ko")
    mp3_buffer = BytesIO()
    tts.write_to_fp(mp3_buffer)
    mp3_buffer.seek(0)
    return mp3_buffer
