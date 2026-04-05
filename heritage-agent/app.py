"""On-Go (to Heritage): Heritage AI Tour Guide Agent."""

import os
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

# ── 프로필 정의 ──
PROFILES = {
    "child": {"icon": "👶", "name": "어린이", "color": "#FF6B6B", "desc": "쉽고 재미있게!"},
    "teenager": {"icon": "🧑‍🎓", "name": "청소년", "color": "#4ECDC4", "desc": "교과서랑 연결!"},
    "adult_male": {"icon": "👨", "name": "성인남성", "color": "#45B7D1", "desc": "구조와 역사 중심"},
    "adult_female": {"icon": "👩", "name": "성인여성", "color": "#DDA0DD", "desc": "감성과 이야기 중심"},
    "expert": {"icon": "🎓", "name": "전문가", "color": "#F7DC6F", "desc": "학술적 심층 분석"},
}


def show_profile_select():
    """넷플릭스 스타일 프로필 선택 화면."""
    st.markdown(
        """
        <style>
        .profile-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 20px;
            margin-top: 40px;
        }
        .profile-card {
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s;
            width: 120px;
        }
        .profile-card:hover {
            transform: scale(1.1);
        }
        .profile-icon {
            font-size: 60px;
            display: block;
            margin-bottom: 8px;
        }
        .profile-name {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .profile-desc {
            font-size: 12px;
            color: #888;
        }
        .title-center {
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle-center {
            text-align: center;
            color: #888;
            margin-bottom: 40px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<h1 class="title-center">On-Go (to Heritage)</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle-center">누가 사용하나요?</p>', unsafe_allow_html=True)

    # 프로필 버튼들 (Streamlit columns 사용)
    cols = st.columns(5)
    for i, (key, profile) in enumerate(PROFILES.items()):
        with cols[i]:
            st.markdown(
                f"""
                <div style="text-align:center; padding:10px;">
                    <div style="font-size:60px;">{profile['icon']}</div>
                    <div style="font-size:14px; font-weight:bold; margin-top:8px;">{profile['name']}</div>
                    <div style="font-size:11px; color:#888;">{profile['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"{profile['name']}", key=f"profile_{key}", use_container_width=True):
                st.session_state["profile"] = key
                st.session_state["profile_name"] = profile["name"]
                st.session_state["profile_icon"] = profile["icon"]
                st.rerun()


def show_main_app():
    """메인 앱 화면."""
    profile = st.session_state["profile"]
    profile_info = PROFILES[profile]

    # 상단 헤더 (프로필 표시 + 전환 버튼)
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.title("On-Go (to Heritage)")
        st.caption(f"Heritage AI Tour Guide Agent | {profile_info['icon']} {profile_info['name']} 모드")
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 프로필 전환", use_container_width=True):
            st.session_state.pop("profile", None)
            st.session_state.pop("result", None)
            st.session_state.pop("_identify_key", None)
            st.rerun()

    persona_key = profile

    tab_guide, tab_map = st.tabs(["📸 가이드", "🗺️ 지도 앨범"])

    # ── 📸 가이드 탭 ──
    with tab_guide:
        uploaded = st.file_uploader("건물/유적지 사진을 올려주세요", type=["jpg", "jpeg", "png"])

        if uploaded:
            image = Image.open(uploaded)
            st.image(image, use_container_width=True)

            # GPS 추출
            gps = extract_gps(image)

            # AI 이미지 인식 (캐싱)
            upload_key = uploaded.name + str(uploaded.size)
            if st.session_state.get("_identify_key") != upload_key:
                with st.spinner("🔍 사진 속 장소를 AI가 분석하고 있습니다..."):
                    ai_result = identify_place(image, gps)
                st.session_state["_identify_key"] = upload_key
                st.session_state["_identify_result"] = ai_result
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

                place_name = st.text_input(
                    "장소 이름을 확인하거나 수정하세요",
                    value=ai_result["name"],
                )
            else:
                st.warning("AI가 장소를 인식하지 못했습니다. 직접 입력해주세요.")
                place_name = st.text_input("장소 이름을 입력하세요", value="")

            if place_name:
                if st.button("🔍 설명 받기", type="primary", use_container_width=True):
                    place_location = ai_result.get("location", "") if ai_result else ""
                    prompt = build_prompt(persona_key, place_name, place_location)

                    with st.spinner("AI가 설명을 준비하고 있습니다..."):
                        explanation = generate_explanation(image, prompt)

                    with st.spinner("음성을 생성하고 있습니다..."):
                        mp3_bytes = text_to_speech(explanation, persona_key)

                    # 좌표 결정
                    if gps:
                        lat, lng = gps["lat"], gps["lng"]
                    elif ai_result and ai_result.get("lat") and ai_result.get("lng"):
                        lat, lng = ai_result["lat"], ai_result["lng"]
                    else:
                        lat, lng = 0, 0

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
                    photo_path = os.path.join(
                        os.path.dirname(__file__), "user_data", "photos", rec.get("photo_filename", "")
                    )
                    if os.path.exists(photo_path):
                        st.image(photo_path, use_container_width=True)
                    st.write(rec["ai_explanation"])
        else:
            st.info("아직 방문 기록이 없습니다. 가이드 탭에서 사진을 올려보세요!")


# ── 라우팅 ──
if "profile" not in st.session_state:
    show_profile_select()
else:
    show_main_app()
