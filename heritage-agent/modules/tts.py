"""텍스트 → 음성 변환 모듈 - 페르소나별 목소리 적용."""

import asyncio
from io import BytesIO

import edge_tts

# 페르소나별 음성 설정
# 한국어 Edge TTS 음성 목록:
#   여성: SunHiNeural, JiMinNeural, SeoHyeonNeural, SoonBokNeural, YuJinNeural
#   남성: InJoonNeural, BongJinNeural, GookMinNeural, HyunsuNeural
PERSONA_VOICE = {
    "child": {
        "voice": "ko-KR-SunHiNeural",     # 밝은 여성 목소리
        "rate": "+15%",                     # 빠르고 활기차게
        "pitch": "+10Hz",                   # 약간 높은 톤
    },
    "teenager": {
        "voice": "ko-KR-YuJinNeural",      # 젊은 여성 목소리
        "rate": "+10%",                     # 약간 빠르게
        "pitch": "+0Hz",
    },
    "adult_male": {
        "voice": "ko-KR-HyunsuNeural",     # 차분한 남성 목소리
        "rate": "+5%",                      # 약간 빠르게
        "pitch": "-5Hz",                    # 약간 낮은 톤
    },
    "adult_female": {
        "voice": "ko-KR-SeoHyeonNeural",   # 따뜻한 여성 목소리
        "rate": "+5%",                      # 약간 빠르게
        "pitch": "+0Hz",
    },
    "expert": {
        "voice": "ko-KR-InJoonNeural",     # 무게감 있는 남성 목소리
        "rate": "+0%",                      # 보통 속도 (진중하게)
        "pitch": "-10Hz",                   # 낮은 톤
    },
}

DEFAULT_VOICE = PERSONA_VOICE["adult_male"]


async def _generate_speech(text, voice, rate, pitch):
    """edge-tts로 음성을 생성한다."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    mp3_buffer = BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buffer.write(chunk["data"])
    mp3_buffer.seek(0)
    return mp3_buffer


def text_to_speech(text, persona="adult_male"):
    """텍스트를 페르소나에 맞는 음성(mp3)으로 변환한다.

    Args:
        text: 설명 텍스트 문자열
        persona: 페르소나 키

    Returns:
        mp3 바이너리 데이터가 담긴 BytesIO 객체
    """
    config = PERSONA_VOICE.get(persona, DEFAULT_VOICE)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    _generate_speech(text, config["voice"], config["rate"], config["pitch"])
                ).result()
            return result
        else:
            return loop.run_until_complete(
                _generate_speech(text, config["voice"], config["rate"], config["pitch"])
            )
    except RuntimeError:
        return asyncio.run(
            _generate_speech(text, config["voice"], config["rate"], config["pitch"])
        )
