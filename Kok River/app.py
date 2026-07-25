"""
Kok River Community Health Risk Assessment App

MVP Streamlit application to help villagers and community leaders along the
Kok River (Chiang Rai) screen for and monitor health risks related to
heavy-metal (arsenic/lead) contamination from transboundary mining.

Run locally with: streamlit run app.py
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import utils

st.set_page_config(
    page_title="แม่น้ำกก | ประเมินความเสี่ยงสุขภาพชุมชน",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .risk-banner {
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    .risk-banner.green {
        background-color: rgba(34, 197, 94, 0.12);
        border: 1px solid rgba(34, 197, 94, 0.55);
    }
    .risk-banner.orange {
        background-color: rgba(245, 158, 11, 0.13);
        border: 1px solid rgba(245, 158, 11, 0.55);
    }
    .risk-banner.red {
        background-color: rgba(239, 68, 68, 0.14);
        border: 2px solid rgba(239, 68, 68, 0.75);
    }
    .hotline-card {
        background-color: rgba(239, 68, 68, 0.08);
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
    }
    .hotline-phone {
        font-size: 1.3rem;
        font-weight: 700;
        color: #ef4444;
    }
    .disclaimer-box {
        background-color: rgba(148, 163, 184, 0.12);
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        font-size: 0.9rem;
        color: inherit;
        opacity: 0.9;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🌊 แอปประเมินความเสี่ยงสุขภาพชุมชน แม่น้ำกก")
st.caption(
    "เครื่องมือคัดกรองเบื้องต้นสำหรับประชาชนและอาสาสมัครสาธารณสุข (อสม.) "
    "ในพื้นที่ลุ่มน้ำกก จังหวัดเชียงราย เพื่อประเมินความเสี่ยงจากการปนเปื้อนสารหนู (Arsenic) และตะกั่ว (Lead)"
)

st.markdown(
    """
    <div class="disclaimer-box">
    ⚠️ <b>ข้อจำกัดของเครื่องมือ:</b> แบบประเมินนี้เป็นเพียงเครื่องมือคัดกรองเบื้องต้นเพื่อสร้างความตระหนักรู้เท่านั้น
    <b>ไม่ใช่การวินิจฉัยทางการแพทย์</b> ผลการประเมินไม่สามารถใช้แทนคำวินิจฉัยของแพทย์หรือการตรวจทางห้องปฏิบัติการได้
    หากมีอาการผิดปกติหรือกังวลเกี่ยวกับสุขภาพ ควรปรึกษาเจ้าหน้าที่สาธารณสุขหรือแพทย์โดยตรง
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

tab_checker, tab_dashboard = st.tabs(
    ["📋 แบบประเมินความเสี่ยงส่วนบุคคล", "📊 แดชบอร์ดผู้นำชุมชน / อสม."]
)

# ---------------------------------------------------------------------------
# TAB 1 — Symptom & Exposure Risk Checker
# ---------------------------------------------------------------------------
with tab_checker:
    st.subheader("📋 แบบสอบถามความเสี่ยงด้านสุขภาพ")
    st.write("กรุณาตอบคำถามตามความเป็นจริง เพื่อประเมินระดับความเสี่ยงของท่าน")

    with st.form("risk_form"):
        col1, col2 = st.columns(2)

        with col1:
            # The district does not change the risk score -- the exposure baseline
            # is uniform across the basin (see LOCATION_BASELINE_SCORE in utils.py).
            # It is used to surface the nearest hospital, and the label says so.
            district = st.selectbox(
                "📍 ท่านอาศัยอยู่ในอำเภอใด",
                options=list(utils.DISTRICTS.keys()),
                help="ใช้สำหรับแนะนำโรงพยาบาลและหน่วยบริการใกล้บ้านท่าน ไม่มีผลต่อคะแนนความเสี่ยง",
            )

            water_uses = st.multiselect(
                "💧 ท่านใช้น้ำจากแม่น้ำกก (หรือแหล่งน้ำที่เชื่อมกับแม่น้ำกก) ในลักษณะใดบ้าง",
                options=list(utils.WATER_USES.keys()),
                help="เลือกได้มากกว่า 1 ข้อ",
            )

        with col2:
            fish_frequency = st.radio(
                "🐟 ท่านรับประทานปลาหรือสัตว์น้ำที่จับจากแม่น้ำกกบ่อยเพียงใด",
                options=list(utils.FISH_FREQUENCY.keys()),
            )

        st.markdown("##### 🩺 ท่านมีอาการต่อไปนี้หรือไม่ (เลือกได้มากกว่า 1 ข้อ)")
        symptoms = st.multiselect(
            "อาการที่พบ",
            options=list(utils.SYMPTOMS.keys()),
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("🔍 ประเมินความเสี่ยง", width="stretch")

    # Every widget has a default, so the form can be submitted with nothing
    # answered. Scoring that yields the baseline 5 -> a confident "low risk"
    # all-clear for someone who told us nothing. Refuse instead.
    if submitted:
        if utils.is_empty_submission(water_uses, fish_frequency, symptoms):
            st.session_state.pop("risk_result", None)
            st.session_state.pop("risk_district", None)
            st.warning(
                "⚠️ **ยังไม่สามารถประเมินได้** เนื่องจากท่านยังไม่ได้เลือกคำตอบใด ๆ "
                "กรุณาตอบอย่างน้อย 1 ข้อ (การใช้น้ำ การกินปลา หรืออาการที่พบ) "
                "แล้วกดประเมินอีกครั้ง — การไม่ตอบคำถามไม่ได้แปลว่าท่านไม่มีความเสี่ยง"
            )
        else:
            st.session_state["risk_result"] = utils.calculate_risk_score(
                water_uses=water_uses,
                fish_frequency=fish_frequency,
                symptoms=symptoms,
            )
            st.session_state["risk_district"] = district

    # Rendered from session state rather than from `submitted` so the verdict
    # survives any rerun that isn't the submit itself.
    result = st.session_state.get("risk_result")

    if result is not None:
        result_district = st.session_state.get("risk_district", district)

        st.divider()
        st.markdown("### ผลการประเมิน")

        m1, m2, m3 = st.columns(3)
        m1.metric("อำเภอ", utils.DISTRICTS[result_district]["name_th"])
        m2.metric("คะแนนความเสี่ยง", f"{result.score} คะแนน")
        m3.metric("ระดับความเสี่ยง", f"{result.emoji} {result.label_th}")

        st.markdown(
            f"""
            <div class="risk-banner {result.color}">
            {result.emoji} <b>ระดับความเสี่ยง: {result.label_th}</b><br>
            คะแนนรวม: {result.score} คะแนน
            </div>
            """,
            unsafe_allow_html=True,
        )

        # The level is never raised silently -- if a hallmark symptom overrode the
        # arithmetic, say so and name the symptom that did it.
        if result.escalated_by_symptoms:
            if len(result.escalating_symptoms) >= 2:
                st.warning(
                    "ℹ️ **เหตุผลที่ยกระดับความเสี่ยง:** ท่านมีทั้ง *ผื่น/แผลผิดปกติที่ผิวหนัง* "
                    "และ *อาการชาที่มือ/เท้า* ซึ่งเป็นอาการที่พบร่วมกันได้ในผู้ที่ได้รับสารหนูเรื้อรัง "
                    "จึงควรได้รับการตรวจ แม้คะแนนรวมจะยังไม่ถึงเกณฑ์ก็ตาม"
                )
            else:
                st.warning(
                    f"ℹ️ **เหตุผลที่ยกระดับความเสี่ยง:** ท่านมีอาการ *{result.escalating_symptoms[0]}* "
                    "ซึ่งเป็นอาการที่จำเพาะต่อการได้รับสารหนูเรื้อรัง "
                    "จึงควรเข้ารับการตรวจ แม้คะแนนรวมจะยังไม่ถึงเกณฑ์ก็ตาม"
                )

        st.markdown("#### ✅ คำแนะนำสำหรับท่าน")
        for rec in utils.get_recommendations(result.level, has_symptoms=result.has_symptoms):
            st.markdown(f"- {rec}")

        if result.level == "high":
            st.markdown("---")

            # A high score with no symptoms is an exposure problem, not a medical
            # emergency -- routing an asymptomatic person to 1669 (ambulance
            # dispatch) is a false alarm. Different heading, different hotlines.
            if result.has_symptoms:
                st.error(
                    "🚨 **ท่านมีความเสี่ยงสูง และมีอาการที่ควรได้รับการตรวจ "
                    "กรุณาติดต่อหน่วยงานสาธารณสุขโดยด่วน**"
                )
            else:
                st.warning(
                    "🔴 **ท่านมีความเสี่ยงสูงจากการสัมผัสสารปนเปื้อน แต่ยังไม่มีอาการ** "
                    "ไม่ใช่กรณีฉุกเฉิน แต่ควรติดต่อขอรับการตรวจคัดกรองภายใน 1-2 สัปดาห์ "
                    "ตามเบอร์ด้านล่าง (หากมีอาการเกิดขึ้น ให้โทร 1669 ทันที)"
                )

            for hotline in utils.get_hotlines_for_district(
                result_district, has_symptoms=result.has_symptoms
            ):
                phone_line = (
                    f'<span class="hotline-phone">📞 {hotline["phone"]}</span><br>'
                    if hotline["phone"] != "-"
                    else '<span style="font-size:0.85rem; font-style:italic;">⚠️ เบอร์ตรงยังไม่ยืนยัน</span><br>'
                )
                st.markdown(
                    f"""
                    <div class="hotline-card">
                    <b>{hotline['name']}</b><br>
                    {phone_line}
                    <span style="font-size:0.85rem;">{hotline['note']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.caption(utils.HOTLINE_DISCLAIMER)

# ---------------------------------------------------------------------------
# TAB 2 — Community Leader Dashboard & Simulation Map
# ---------------------------------------------------------------------------
with tab_dashboard:
    st.subheader("📊 แดชบอร์ดสำหรับผู้นำชุมชนและ อสม.")
    st.info(
        "ℹ️ ข้อมูลในแดชบอร์ดนี้เป็น **ข้อมูลจำลอง (Mock Data)** สำหรับสาธิตการทำงานของระบบ MVP เท่านั้น "
        "ยังไม่ใช่ข้อมูลจากการสำรวจจริงในพื้นที่"
    )

    district_df = utils.generate_mock_district_risk()
    trend_df = utils.generate_mock_symptom_trend()
    map_df = utils.generate_mock_map_points()

    overall_high = district_df["ความเสี่ยงสูง (%)"].mean()
    overall_medium = district_df["ความเสี่ยงปานกลาง (%)"].mean()
    total_reports = int(trend_df["จำนวนรายงานอาการ"].sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("จำนวนอำเภอที่ติดตาม", len(utils.DISTRICTS))
    k2.metric("เฉลี่ยความเสี่ยงสูง", f"{overall_high:.1f}%")
    k3.metric("เฉลี่ยความเสี่ยงปานกลาง", f"{overall_medium:.1f}%")
    k4.metric(f"รายงานอาการสะสม ({len(trend_df)} สัปดาห์)", f"{total_reports:,} ราย")

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("##### 🏘️ สัดส่วนประชากรกลุ่มเสี่ยงต่อแต่ละอำเภอ")
        fig_bar = px.bar(
            district_df,
            x="district",
            y=["ความเสี่ยงสูง (%)", "ความเสี่ยงปานกลาง (%)", "ความเสี่ยงต่ำ (%)"],
            barmode="stack",
            color_discrete_map={
                "ความเสี่ยงสูง (%)": "#ef4444",
                "ความเสี่ยงปานกลาง (%)": "#f59e0b",
                "ความเสี่ยงต่ำ (%)": "#22c55e",
            },
            labels={"district": "อำเภอ", "value": "สัดส่วน (%)", "variable": "ระดับความเสี่ยง"},
        )
        fig_bar.update_layout(legend_title_text="", height=420)
        st.plotly_chart(fig_bar, width="stretch")

    with col_right:
        st.markdown("##### 📈 แนวโน้มการรายงานอาการรายสัปดาห์")
        fig_line = go.Figure()
        fig_line.add_trace(
            go.Scatter(
                x=trend_df["สัปดาห์ (Week starting)"],
                y=trend_df["จำนวนรายงานอาการ"],
                mode="lines+markers",
                line=dict(color="#ef4444", width=3),
                marker=dict(size=7),
                fill="tozeroy",
                fillcolor="rgba(239, 68, 68, 0.1)",
            )
        )
        fig_line.update_layout(
            height=420,
            xaxis_title="สัปดาห์",
            yaxis_title="จำนวนรายงานอาการ",
        )
        st.plotly_chart(fig_line, width="stretch")

    st.divider()

    st.markdown("##### 🗺️ แผนที่จำลองการกระจายความเสี่ยงตามแนวแม่น้ำกก")
    fig_map = px.scatter_map(
        map_df,
        lat="lat",
        lon="lon",
        color="risk_level",
        color_discrete_map={"ต่ำ": "#22c55e", "ปานกลาง": "#f59e0b", "สูง": "#ef4444"},
        hover_data={"district": True, "lat": False, "lon": False},
        zoom=8,
        height=520,
    )
    fig_map.update_layout(
        map_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        legend_title_text="ระดับความเสี่ยง",
    )
    st.plotly_chart(fig_map, width="stretch")

    st.divider()
    with st.expander("📄 ดูข้อมูลดิบ (Raw mock data)"):
        st.markdown("**สัดส่วนกลุ่มเสี่ยงตามอำเภอ**")
        st.dataframe(district_df, width="stretch", hide_index=True)
        st.markdown("**แนวโน้มรายงานอาการ**")
        st.dataframe(trend_df, width="stretch", hide_index=True)
