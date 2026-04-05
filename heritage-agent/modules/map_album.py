"""Step 7: Folium 지도 앨범 생성 모듈."""

import base64
import os
from collections import defaultdict

import folium

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_data", "photos")
DEFAULT_CENTER = (37.5885, 127.0245)  # 홍릉/의릉 중간 지점
DEFAULT_ZOOM = 16


def _photo_to_base64(photo_filename):
    """사진 파일을 base64 문자열로 변환한다."""
    path = os.path.join(PHOTOS_DIR, photo_filename)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_popup_html(place_name, records):
    """마커 팝업용 HTML을 생성한다."""
    html_parts = [f'<div style="width:250px"><h4>{place_name}</h4>']

    for rec in records[:5]:  # 최대 5장까지 표시
        b64 = _photo_to_base64(rec["photo_filename"])
        if b64:
            html_parts.append(
                f'<img src="data:image/jpeg;base64,{b64}" width="230">'
            )
        html_parts.append(
            f'<p style="font-size:12px;color:gray;">{rec["date"]} 방문</p>'
        )
        explanation_preview = rec["ai_explanation"][:100]
        html_parts.append(
            f'<p style="font-size:13px;">{explanation_preview}...</p>'
        )

    html_parts.append("</div>")
    return "\n".join(html_parts)


def create_map(records):
    """방문 기록들을 Folium 지도에 표시한다.

    Args:
        records: 방문 기록 리스트

    Returns:
        folium.Map 객체
    """
    m = folium.Map(location=DEFAULT_CENTER, zoom_start=DEFAULT_ZOOM)

    if not records:
        folium.Marker(
            location=DEFAULT_CENTER,
            popup="아직 방문 기록이 없습니다. 가이드 탭에서 사진을 올려보세요!",
            icon=folium.Icon(color="gray", icon="info-sign"),
        ).add_to(m)
        return m

    # 같은 장소의 기록을 그룹화
    grouped = defaultdict(list)
    for rec in records:
        grouped[rec["place_name"]].append(rec)

    for place_name, place_records in grouped.items():
        first = place_records[0]
        color = "red" if first["category"] == "홍릉" else "blue"

        popup_html = _build_popup_html(place_name, place_records)
        popup = folium.Popup(popup_html, max_width=280)

        folium.Marker(
            location=(first["lat"], first["lng"]),
            popup=popup,
            icon=folium.Icon(color=color, icon="flag"),
        ).add_to(m)

    return m
