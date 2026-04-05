"""On-Go (to Heritage): Heritage AI Tour Guide Agent."""

import streamlit as st
from PIL import Image
from streamlit_folium import st_folium

from modules.gps_extractor import extract_gps
from modules.persona import build_prompt, PERSONA_LABELS
from modules.gemini_client import generate_explanation, identify_place
from modules.tts import text_to_speech
from modules.storage import save_record, load_all_records
from modules.map_album import create_map

st.set_page_config(page_title="On-Go (to Heritage)", layout="centered")
st.title("On-Go (to Heritage)")
st.caption("Heritage AI Tour Guide Agent")

tab_guide, tab_map = st.tabs(["📸 가이드", "🗺️ 지도 앨범"])

# ── 📸 가이드 탭 ──
with tab_guide:
    uploaded = st.file_uploader("건물/유적지 사진을 올려주세요", type=["jpg", "jpeg", "png"])

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

        # GPS 추출
        gps = extract_gps(image)

        # AI 이미지 인식 (캐싱: 같은 사진이면 다시 호출하지 않음)
        upload_key = uploaded.name + str(uploaded.size)
        if st.session_state.get("_identify_key") != upload_key:
            with st.spinner("🔍 사진 속 장소를 AI가 분석하고 있습니다..."):
                ai_result = identify_place(image, gps)
            st.session_state["_identify_key"] = upload_key
            st.session_state["_identify_result"] = ai_result
            # 새 사진이면 이전 결과 클리어
            st.session_state.pop("result", None)
        else:
            ai_result = st.session_state.get("_identify_result")

        # 인식 결과 표시
        st.subheader("📍 장소 인식 결과")

        if gps:
            st.info(f"🛰️ GPS 감지: 위도 {gps['lat']:.4f}, 경도 {gps['lng']:.4f}")

        if ai_result:
            confidence_emoji = {"높음": "🟢", "보통": "🟡", "낮음": "🔴"}.get(
                ai_result.get("confidence", ""), "⚪"
            )
            coord_str = ""
            if ai_result.get("lat") and ai_result.get("lng"):
                coord_str = f"\n\n🗺️ 추정 좌표: ({ai_result['lat']:.4f}, {ai_result['lng']:.4f})"
            st.success(
                f"🤖 AI 인식: **{ai_result['name']}**\n\n"
                f"📌 위치: {ai_result.get('location', '알 수 없음')} | "
                f"🏷️ 분류: {ai_result.get('category', '기타')} | "
                f"{confidence_emoji} 확신도: {ai_result.get('confidence', '알 수 없음')}\n\n"
                f"💡 근거: {ai_result.get('description', '')}"
                f"{coord_str}"
            )

            # 장소명 수정 가능
            place_name = st.text_input(
                "장소 이름을 확인하거나 수정하세요",
                value=ai_result["name"],
            )
        else:
            st.warning("AI가 장소를 인식하지 못했습니다. 직접 입력해주세요.")
            place_name = st.text_input("장소 이름을 입력하세요", value="")

        if place_name:
            # 설명 받기 버튼
            if st.button("🔍 설명 받기", type="primary", use_container_width=True):
                place_location = ai_result.get("location", "") if ai_result else ""
                prompt = build_prompt(persona_key, place_name, place_location)

                with st.spinner("AI가 설명을 준비하고 있습니다..."):
                    explanation = generate_explanation(image, prompt)

                with st.spinner("음성을 생성하고 있습니다..."):
                    mp3_bytes = text_to_speech(explanation)

                # 좌표 결정: GPS 우선 → AI 추정 좌표 fallback
                if gps:
                    lat, lng = gps["lat"], gps["lng"]
                elif ai_result and ai_result.get("lat") and ai_result.get("lng"):
                    lat, lng = ai_result["lat"], ai_result["lng"]
                else:
                    lat, lng = 0, 0

                # 저장용 place_info 구성
                place_info = {
                    "name": place_name,
                    "location": ai_result.get("location", "") if ai_result else "",
                    "category": ai_result.get("category", "기타") if ai_result else "기타",
                    "lat": lat,
                    "lng": lng,
                }
                save_record(image, place_info, persona_key, explanation)

                st.session_state["result"] = {
                    "place_name": place_name,
                    "location": place_info["location"],
                    "explanation": explanation,
                    "mp3_bytes": mp3_bytes,
                }

            # 결과 표시
            if "result" in st.session_state:
                result = st.session_state["result"]
                st.divider()
                location_str = f" ({result['location']})" if result.get("location") else ""
                st.subheader(f"📍 {result['place_name']}{location_str}")
                st.write(result["explanation"])
                st.audio(result["mp3_bytes"], format="audio/mp3")
                st.success("✅ 방문 기록이 저장되었습니다!")

# ── 🗺️ 지도 앨범 탭 ──
with tab_map:
    records = load_all_records()
    m = create_map(records)
    st_folium(m, width=700, height=500, use_container_width=True)

    if records:
        st.divider()
        st.subheader("📋 방문 기록")
        for rec in sorted(records, key=lambda r: r["date"] + r["time"], reverse=True):
            location_str = f" - {rec.get('location', '')}" if rec.get("location") else ""
            with st.expander(
                f"{rec['date']} - {rec['place_name']}{location_str} "
                f"({PERSONA_LABELS.get(rec['persona'], rec['persona'])})"
            ):
                # 저장된 사진 표시
                import os
                photo_path = os.path.join(
                    os.path.dirname(__file__), "user_data", "photos", rec.get("photo_filename", "")
                )
                if os.path.exists(photo_path):
                    st.image(photo_path, use_container_width=True)
                st.write(rec["ai_explanation"])
    else:
        st.info("아직 방문 기록이 없습니다. 가이드 탭에서 사진을 올려보세요!")
