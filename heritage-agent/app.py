"""On-Go (to Heritage): Heritage AI Tour Guide Agent."""

import os
import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

from modules.gps_extractor import extract_gps
from modules.place_matcher import find_nearest_place, load_places
from modules.persona import build_prompt, PERSONA_LABELS
from modules.gemini_client import generate_explanation, identify_place
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

        # 장소 자동 인식
        places = load_places()
        place_names = [p["name"] for p in places]

        # GPS 추출
        gps = extract_gps(image)
        gps_match = None
        if gps:
            gps_match = find_nearest_place(gps["lat"], gps["lng"])

        # AI 이미지 인식 (캐싱)
        upload_key = uploaded.name + str(uploaded.size)
        if st.session_state.get("_identify_key") != upload_key:
            with st.spinner("🔍 사진 속 장소를 AI가 분석하고 있습니다..."):
                ai_result = identify_place(image, place_names)
            st.session_state["_identify_key"] = upload_key
            st.session_state["_identify_result"] = ai_result
        else:
            ai_result = st.session_state.get("_identify_result")

        # 인식 결과 표시
        st.subheader("📍 장소 인식 결과")

        if gps_match:
            st.success(f"🛰️ GPS 감지: **{gps_match['name']}** ({gps_match['distance_m']}m)")

        if ai_result:
            confidence_emoji = {"높음": "🟢", "보통": "🟡", "낮음": "🔴"}.get(ai_result.get("confidence", ""), "⚪")
            st.success(
                f"🤖 AI 인식: **{ai_result['matched']}** "
                f"{confidence_emoji} 확신도: {ai_result.get('confidence', '알 수 없음')}\n\n"
                f"근거: {ai_result.get('description', '')}"
            )

        if not gps_match and not ai_result:
            st.warning("GPS와 AI 인식 모두 실패했습니다. 아래에서 직접 선택해주세요.")

        # 장소 선택 (추천 결과를 기본값으로)
        default_name = None
        if ai_result and ai_result["matched"] in place_names:
            default_name = ai_result["matched"]
        elif gps_match:
            default_name = gps_match["name"]

        default_idx = place_names.index(default_name) if default_name else 0
        selected_name = st.selectbox(
            "장소를 확인하거나 변경하세요",
            place_names,
            index=default_idx,
        )
        place_info = next(p for p in places if p["name"] == selected_name)
        place_info["distance_m"] = gps_match["distance_m"] if gps_match and gps_match["name"] == selected_name else 0

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

            # 음성 생성
            with st.spinner("음성을 생성하고 있습니다..."):
                mp3_bytes = text_to_speech(explanation)

            # 자동 저장
            save_record(image, place_info, persona_key, explanation)

            # 결과를 session_state에 저장
            st.session_state["result"] = {
                "place_name": place_info["name"],
                "explanation": explanation,
                "mp3_bytes": mp3_bytes,
                "category": place_info["category"],
            }

        # session_state에 결과가 있으면 표시
        if "result" in st.session_state:
            result = st.session_state["result"]
            st.subheader(f"📍 {result['place_name']}")
            st.write(result["explanation"])
            st.audio(result["mp3_bytes"], format="audio/mp3")
            st.success("✅ 방문 기록이 저장되었습니다!")

            # 근처 다른 볼거리
            all_places = load_places()
            nearby = [
                p for p in all_places
                if p["category"] == result["category"] and p["name"] != result["place_name"]
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
