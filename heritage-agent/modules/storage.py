"""방문 기록 저장/불러오기 모듈 - 전세계 장소 대응."""

import json
import os
from datetime import datetime

from PIL import Image

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data")
RECORDS_PATH = os.path.join(BASE_DIR, "records.json")
PROFILES_PATH = os.path.join(BASE_DIR, "profiles.json")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")


def _ensure_dirs():
    os.makedirs(PHOTOS_DIR, exist_ok=True)


def _load_json():
    _ensure_dirs()
    if not os.path.exists(RECORDS_PATH):
        return {"records": []}
    with open(RECORDS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_json(data):
    _ensure_dirs()
    with open(RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _generate_record_id(data):
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"rec_{today}_"
    existing = [r["id"] for r in data["records"] if r["id"].startswith(prefix)]
    seq = len(existing) + 1
    return f"{prefix}{seq:03d}"


def save_record(photo, place_info, persona, explanation):
    """방문 기록을 저장한다.

    Args:
        photo: PIL Image 객체
        place_info: {"name": str, "location": str, "category": str, "lat": float, "lng": float}
        persona: 페르소나 키
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
        "place_name": place_info.get("name", "알 수 없는 장소"),
        "location": place_info.get("location", ""),
        "lat": place_info.get("lat", 0),
        "lng": place_info.get("lng", 0),
        "category": place_info.get("category", "기타"),
        "persona": persona,
        "ai_explanation": explanation,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
    }

    data["records"].append(record)
    _save_json(data)
    return record


def load_all_records():
    data = _load_json()
    return data["records"]


def load_records_by_place(place_name):
    records = load_all_records()
    return [r for r in records if r["place_name"] == place_name]


# ── 프로필 관리 ──

def _load_profiles_json():
    _ensure_dirs()
    if not os.path.exists(PROFILES_PATH):
        return {"profiles": []}
    with open(PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_profiles_json(data):
    _ensure_dirs()
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_profile(profile):
    """프로필을 저장한다. 같은 이름이면 업데이트.

    Args:
        profile: {"name": str, "age": int, "gender": str, "mbti": str, "expert_mode": bool}
    """
    data = _load_profiles_json()
    existing = [i for i, p in enumerate(data["profiles"]) if p["name"] == profile["name"]]
    if existing:
        data["profiles"][existing[0]] = profile
    else:
        data["profiles"].append(profile)
    _save_profiles_json(data)


def load_all_profiles():
    data = _load_profiles_json()
    return data["profiles"]


def delete_profile(name):
    data = _load_profiles_json()
    data["profiles"] = [p for p in data["profiles"] if p["name"] != name]
    _save_profiles_json(data)
