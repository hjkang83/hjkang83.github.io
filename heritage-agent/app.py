"""On-Go (to Heritage): Heritage AI Tour Guide Agent."""

import os
import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

from modules.gps_extractor import extract_gps
from modules.place_matcher import find_nearest_place, load_places
from modules.persona import build_prompt, PERSONA_LABELS
from modules.gemini_client import generate_explanation
from modules.tts import text_to_speech
from modules.storage import save_record, load_all_records
from modules.map_album import create_map

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

st.set_page_config(page_title="On-Go (to Heritage)", layout="centered")
st.title("On-Go (to Heritage)")
st.caption("Heritage AI Tour Guide Agent")

tab_guide, tab_map = st.tabs(["📸 가이드", "🗺️ 지도 앨범"])

# ── 📸 가이드 탭 ──
with tab_guide:
    uploaded = st.file_uploader("유적지 사진을 올려주세요", type=["jpg", "jpeg", "png"])

    if uploaded:
        image = Image.open(uploaded)
        st.image(image, use_container_width=True)

        # 페르소나 선택
        persona_key = st.radio(
            "설명 스타일을 선택하세요",
            options=list(PERSONA_LABELS.keys()),
            format_func=lambda k: PERSONA_LABELS[k],
            horizontal=True,
        )

        # GPS 추출 시도
        gps = extract_gps(image)

        place_info = None

        if gps:
            place_info = find_nearest_place(gps["lat"], gps["lng"])
            if place_info:
                st.info(f"📍 감지된 장소: **{place_info['name']}** ({place_info['distance_m']}m)")
            else:
                st.warning("📍 GPS는 감지되었으나 등록된 장소 근처(500m 이내)가 아닙니다. 아래에서 장소를 선택해주세요.")

        if not gps or not place_info:
            if not gps:
                st.warning("이 사진에 위치 정보가 없습니다. 장소를 직접 선택해주세요.")
            places = load_places()
            place_names = [p["name"] for p in places]
            selected_name = st.selectbox("장소 선택", place_names)
            place_info = next(p for p in places if p["name"] == selected_name)
            place_info["distance_m"] = 0

        # 설명 받기 버튼
        if st.button("🔍 설명 받기", type="primary", use_container_width=True):
            # 참고 텍스트 로드
            data_file_path = os.path.join(DATA_DIR, place_info["data_file"])
            if os.path.exists(data_file_path):
                with open(data_file_path, encoding="utf-8") as f:
                    reference_text = f.read()
            else:
                reference_text = f"{place_info['name']}에 대한 참고 자료가 아직 준비되지 않았습니다."

            # 프롬프트 생성
            prompt = build_prompt(persona_key, place_info["name"], reference_text)

            # AI 설명 생성
            with st.spinner("AI가 설명을 준비하고 있습니다..."):
                explanation = generate_explanation(image, prompt)

            st.subheader(f"📍 {place_info['name']}")
            st.write(explanation)

            # 음성 재생
            with st.spinner("음성을 생성하고 있습니다..."):
                mp3_bytes = text_to_speech(explanation)
            st.audio(mp3_bytes, format="audio/mp3")

            # 자동 저장
            save_record(image, place_info, persona_key, explanation)
            st.success("✅ 방문 기록이 저장되었습니다!")

            # 근처 다른 볼거리
            all_places = load_places()
            nearby = [
                p for p in all_places
                if p["category"] == place_info["category"] and p["name"] != place_info["name"]
            ]
            if nearby:
                st.divider()
                st.subheader("🏛️ 근처 다른 볼거리")
                for p in nearby:
                    st.write(f"- {p['name']}")

# ── 🗺️ 지도 앨범 탭 ──
with tab_map:
    records = load_all_records()
    m = create_map(records)
    st_folium(m, width=700, height=500, use_container_width=True)

    if records:
        st.divider()
        st.subheader("📋 방문 기록")
        for rec in sorted(records, key=lambda r: r["date"] + r["time"], reverse=True):
            with st.expander(f"{rec['date']} - {rec['place_name']} ({PERSONA_LABELS.get(rec['persona'], rec['persona'])})"):
                st.write(rec["ai_explanation"])
    else:
        st.info("아직 방문 기록이 없습니다. 가이드 탭에서 사진을 올려보세요!")
