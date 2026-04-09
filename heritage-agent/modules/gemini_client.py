"""Gemini API 호출 모듈 - 전세계 건물/랜드마크 인식 및 설명 생성."""

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
    """사진과 프롬프트를 Gemini에 보내고 설명 텍스트를 받는다."""
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        return f"⚠️ AI 설명 생성에 실패했습니다. 잠시 후 다시 시도해주세요.\n(오류: {e})"


def identify_place(image, gps_info=None):
    """사진 속 건물/랜드마크를 Gemini로 인식하고 좌표도 추정한다.

    Args:
        image: PIL Image 객체
        gps_info: {"lat": float, "lng": float} 또는 None

    Returns:
        {"name": str, "location": str, "confidence": str,
         "description": str, "category": str, "lat": float, "lng": float}
        또는 인식 실패 시 None
    """
    gps_hint = ""
    if gps_info:
        gps_hint = f"\n참고: 이 사진의 GPS 좌표는 위도 {gps_info['lat']:.4f}, 경도 {gps_info['lng']:.4f} 입니다.\n"

    prompt = (
        "이 사진에 보이는 건물, 랜드마크, 유적지, 기념물 등을 분석해줘.\n"
        f"{gps_hint}\n"
        "전세계 어떤 건물이든 가능해. 대학 건물, 성당, 궁전, 탑, 다리, 현대 건축물 등 모두 포함.\n"
        "반드시 아래 형식으로만 답해줘 (다른 말 하지 마):\n"
        "이름: [건물/장소의 공식 명칭]\n"
        "위치: [도시, 국가]\n"
        "위도: [숫자, 예: 37.4419]\n"
        "경도: [숫자, 예: -122.1430]\n"
        "분류: [대학, 종교건축, 궁전, 유적지, 현대건축, 탑, 다리, 기념물, 기타 중 택1]\n"
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
            if line.startswith("이름:"):
                result["name"] = line.replace("이름:", "").strip()
            elif line.startswith("위치:"):
                result["location"] = line.replace("위치:", "").strip()
            elif line.startswith("위도:"):
                try:
                    result["lat"] = float(line.replace("위도:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("경도:"):
                try:
                    result["lng"] = float(line.replace("경도:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("분류:"):
                result["category"] = line.replace("분류:", "").strip()
            elif line.startswith("확신도:"):
                result["confidence"] = line.replace("확신도:", "").strip()
            elif line.startswith("근거:"):
                result["description"] = line.replace("근거:", "").strip()

        if "name" in result:
            return result
        return None
    except Exception:
        return None


def recommend_nearby_places(place_name, place_location, lat, lng, persona_prompt):
    """현재 장소 주변의 유적지/랜드마크를 페르소나에 맞게 추천한다.

    Args:
        place_name: 현재 방문 중인 장소 이름
        place_location: 위치 정보 (도시, 국가)
        lat: 위도
        lng: 경도
        persona_prompt: 페르소나 특성 설명 문자열

    Returns:
        list of {"name", "location", "category", "lat", "lng",
                 "distance", "description", "reason", "image_query"}
        또는 실패 시 빈 리스트
    """
    coord_info = ""
    if lat and lng:
        coord_info = f"현재 위치 좌표: 위도 {lat:.4f}, 경도 {lng:.4f}\n"

    prompt = (
        f"사용자가 지금 '{place_name}' ({place_location})을(를) 방문하고 있어.\n"
        f"{coord_info}\n"
        f"{persona_prompt}\n\n"
        "이 장소 근처(같은 도시 또는 반경 30km 이내)에서 이 사용자가 좋아할 만한 "
        "유적지, 랜드마크, 건축물을 5개 추천해줘.\n"
        "현재 방문 중인 장소는 제외해.\n\n"
        "반드시 아래 형식으로만 답해줘 (다른 말 하지 마).\n"
        "각 추천을 ---로 구분해줘:\n\n"
        "이름: [장소 공식 명칭]\n"
        "위치: [도시, 국가]\n"
        "분류: [대학, 종교건축, 궁전, 유적지, 현대건축, 탑, 다리, 기념물, 박물관, 정원, 기타 중 택1]\n"
        "위도: [숫자]\n"
        "경도: [숫자]\n"
        "거리: [현재 위치에서 대략적 거리, 예: 1.2km]\n"
        "설명: [이 장소에 대한 2~3문장 소개]\n"
        "추천이유: [이 사용자에게 특별히 추천하는 이유 1문장]\n"
        "검색어: [이 장소의 대표 사진을 찾기 위한 영문 검색어]\n"
        "---"
    )
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        text = response.text.strip()

        places = []
        blocks = text.split("---")
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            place = {}
            for line in block.split("\n"):
                line = line.strip()
                if line.startswith("이름:"):
                    place["name"] = line.replace("이름:", "").strip()
                elif line.startswith("위치:"):
                    place["location"] = line.replace("위치:", "").strip()
                elif line.startswith("분류:"):
                    place["category"] = line.replace("분류:", "").strip()
                elif line.startswith("위도:"):
                    try:
                        place["lat"] = float(line.replace("위도:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("경도:"):
                    try:
                        place["lng"] = float(line.replace("경도:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("거리:"):
                    place["distance"] = line.replace("거리:", "").strip()
                elif line.startswith("설명:"):
                    place["description"] = line.replace("설명:", "").strip()
                elif line.startswith("추천이유:"):
                    place["reason"] = line.replace("추천이유:", "").strip()
                elif line.startswith("검색어:"):
                    place["image_query"] = line.replace("검색어:", "").strip()
            if "name" in place:
                places.append(place)

        return places[:5]
    except Exception:
        return []


def fetch_place_image(query):
    """Wikipedia에서 장소 사진 URL을 가져온다.

    Args:
        query: 영문 검색어 (예: "Gyeongbokgung Palace")

    Returns:
        이미지 URL 문자열 또는 None
    """
    import urllib.request
    import urllib.parse
    import json

    try:
        # Wikipedia 검색으로 페이지 찾기
        search_url = (
            "https://en.wikipedia.org/w/api.php?"
            + urllib.parse.urlencode({
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
                "format": "json",
            })
        )
        with urllib.request.urlopen(search_url, timeout=5) as resp:
            search_data = json.loads(resp.read())

        results = search_data.get("query", {}).get("search", [])
        if not results:
            return None

        title = results[0]["title"]

        # 해당 페이지의 대표 이미지 가져오기
        image_url = (
            "https://en.wikipedia.org/w/api.php?"
            + urllib.parse.urlencode({
                "action": "query",
                "titles": title,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 600,
            })
        )
        with urllib.request.urlopen(image_url, timeout=5) as resp:
            image_data = json.loads(resp.read())

        pages = image_data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                return thumb

        return None
    except Exception:
        return None


def get_place_media(query):
    """장소/식당에 대한 사진 URL과 블로그/유튜브 검색 링크를 반환한다.

    Args:
        query: 영문 검색어

    Returns:
        {"image_url": str or None, "blog_url": str, "youtube_url": str,
         "google_image_url": str}
    """
    import urllib.parse

    q = urllib.parse.quote(query)
    return {
        "image_url": fetch_place_image(query),
        "blog_url": f"https://search.naver.com/search.naver?where=post&query={q}",
        "youtube_url": f"https://www.youtube.com/results?search_query={q}+review",
        "google_image_url": f"https://www.google.com/search?q={q}&tbm=isch",
    }


def recommend_nearby_activities(place_name, place_location, lat, lng, persona_prompt):
    """현재 장소 주변의 액티비티/체험을 페르소나에 맞게 추천한다.

    Returns:
        list of {"name", "category", "description", "reason",
                 "duration", "difficulty", "image_query"}
    """
    coord_info = ""
    if lat and lng:
        coord_info = f"현재 위치 좌표: 위도 {lat:.4f}, 경도 {lng:.4f}\n"

    prompt = (
        f"사용자가 지금 '{place_name}' ({place_location})을(를) 방문하고 있어.\n"
        f"{coord_info}\n"
        f"{persona_prompt}\n\n"
        "이 장소 근처에서 이 사용자가 즐길 만한 액티비티/체험/투어/공원/테마파크/박물관 등을 3개 추천해줘.\n"
        "리뷰가 많고 방문자 수가 많은 인기 있는 곳 위주로 추천해줘.\n"
        "해당 지역에서 실제로 유명한 액티비티여야 해. 맛집은 제외해.\n\n"
        "반드시 아래 형식으로만 답해줘 (다른 말 하지 마).\n"
        "각 추천을 ---로 구분해줘:\n\n"
        "이름: [액티비티/장소 이름]\n"
        "분류: [투어, 박물관, 공원, 테마파크, 전망대, 쇼핑, 체험, 스파, 야경, 공연, 기타 중 택1]\n"
        "설명: [이 액티비티의 특징과 경험을 2~3문장으로 소개]\n"
        "추천이유: [이 사용자에게 특별히 추천하는 이유 1문장]\n"
        "소요시간: [예상 소요시간, 예: 1~2시간]\n"
        "난이도: [쉬움, 보통, 활동적 중 택1]\n"
        "검색어: [이 장소의 사진을 찾기 위한 영문 검색어]\n"
        "---"
    )
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        text = response.text.strip()

        places = []
        blocks = text.split("---")
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            place = {}
            for line in block.split("\n"):
                line = line.strip()
                if line.startswith("이름:"):
                    place["name"] = line.replace("이름:", "").strip()
                elif line.startswith("분류:"):
                    place["category"] = line.replace("분류:", "").strip()
                elif line.startswith("설명:"):
                    place["description"] = line.replace("설명:", "").strip()
                elif line.startswith("추천이유:"):
                    place["reason"] = line.replace("추천이유:", "").strip()
                elif line.startswith("소요시간:"):
                    place["duration"] = line.replace("소요시간:", "").strip()
                elif line.startswith("난이도:"):
                    place["difficulty"] = line.replace("난이도:", "").strip()
                elif line.startswith("검색어:"):
                    place["image_query"] = line.replace("검색어:", "").strip()
            if "name" in place:
                places.append(place)

        return places[:3]
    except Exception:
        return []


def recommend_nearby_food(place_name, place_location, lat, lng, persona_prompt):
    """현재 장소 주변의 맛집/액티비티를 페르소나에 맞게 추천한다.

    Returns:
        list of {"name", "category", "description", "reason",
                 "price_range", "rating", "image_query"}
    """
    coord_info = ""
    if lat and lng:
        coord_info = f"현재 위치 좌표: 위도 {lat:.4f}, 경도 {lng:.4f}\n"

    prompt = (
        f"사용자가 지금 '{place_name}' ({place_location})을(를) 방문하고 있어.\n"
        f"{coord_info}\n"
        f"{persona_prompt}\n\n"
        "이 장소 근처에서 이 사용자가 좋아할 만한 맛집이나 카페를 3개 추천해줘.\n"
        "리뷰가 많고 방문자 수가 많은 인기 있는 곳 위주로 추천해줘.\n"
        "해당 지역의 실제로 유명한 식당/카페를 추천해야 해.\n\n"
        "반드시 아래 형식으로만 답해줘 (다른 말 하지 마).\n"
        "각 추천을 ---로 구분해줘:\n\n"
        "이름: [식당/카페 이름]\n"
        "분류: [한식, 양식, 중식, 일식, 카페, 디저트, 분식, 해산물, 퓨전, 기타 중 택1]\n"
        "설명: [이 곳의 대표 메뉴와 분위기를 2~3문장으로 소개]\n"
        "추천이유: [이 사용자에게 특별히 추천하는 이유 1문장]\n"
        "가격대: [저렴, 보통, 고급 중 택1]\n"
        "인기도: [매우높음, 높음, 보통 중 택1]\n"
        "검색어: [이 식당의 사진을 찾기 위한 영문 검색어]\n"
        "---"
    )
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        text = response.text.strip()

        places = []
        blocks = text.split("---")
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            place = {}
            for line in block.split("\n"):
                line = line.strip()
                if line.startswith("이름:"):
                    place["name"] = line.replace("이름:", "").strip()
                elif line.startswith("분류:"):
                    place["category"] = line.replace("분류:", "").strip()
                elif line.startswith("설명:"):
                    place["description"] = line.replace("설명:", "").strip()
                elif line.startswith("추천이유:"):
                    place["reason"] = line.replace("추천이유:", "").strip()
                elif line.startswith("가격대:"):
                    place["price_range"] = line.replace("가격대:", "").strip()
                elif line.startswith("인기도:"):
                    place["rating"] = line.replace("인기도:", "").strip()
                elif line.startswith("검색어:"):
                    place["image_query"] = line.replace("검색어:", "").strip()
            if "name" in place:
                places.append(place)

        return places[:3]
    except Exception:
        return []
