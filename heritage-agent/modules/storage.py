"""Step 6: 방문 기록 저장/불러오기 모듈."""

import json
import os
from datetime import datetime

from PIL import Image

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data")
RECORDS_PATH = os.path.join(BASE_DIR, "records.json")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")


def _ensure_dirs():
    """user_data 디렉토리 구조를 보장한다."""
    os.makedirs(PHOTOS_DIR, exist_ok=True)


def _load_json():
    """records.json을 로드한다. 없으면 빈 구조를 생성한다."""
    _ensure_dirs()
    if not os.path.exists(RECORDS_PATH):
        return {"records": []}
    with open(RECORDS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_json(data):
    """records.json에 저장한다."""
    _ensure_dirs()
    with open(RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _generate_record_id(data):
    """rec_{날짜}_{3자리순번} 형식의 ID를 생성한다."""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"rec_{today}_"
    existing = [r["id"] for r in data["records"] if r["id"].startswith(prefix)]
    seq = len(existing) + 1
    return f"{prefix}{seq:03d}"


def save_record(photo, place_info, persona, explanation):
    """방문 기록을 저장한다.

    Args:
        photo: PIL Image 객체
        place_info: place_matcher에서 반환된 장소 dict
        persona: 페르소나 키 ("child" | "general" | "expert")
        explanation: AI가 생성한 설명 텍스트

    Returns:
        저장된 record dict
    """
    data = _load_json()
    record_id = _generate_record_id(data)
    now = datetime.now()

    # 사진을 가로 800px로 리사이즈하여 저장
    width = 800
    ratio = width / photo.width
    height = int(photo.height * ratio)
    resized = photo.resize((width, height), Image.LANCZOS)
    photo_filename = f"{record_id}.jpg"
    resized.save(os.path.join(PHOTOS_DIR, photo_filename), "JPEG", quality=85)

    record = {
        "id": record_id,
        "photo_filename": photo_filename,
        "place_name": place_info["name"],
        "lat": place_info["lat"],
        "lng": place_info["lng"],
        "category": place_info["category"],
        "persona": persona,
        "ai_explanation": explanation,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
    }

    data["records"].append(record)
    _save_json(data)
    return record


def load_all_records():
    """전체 방문 기록을 반환한다."""
    data = _load_json()
    return data["records"]


def load_records_by_place(place_name):
    """특정 장소의 방문 기록만 반환한다."""
    records = load_all_records()
    return [r for r in records if r["place_name"] == place_name]
