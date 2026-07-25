"""
Data handling and scoring logic for the Kok River Community Health Risk Assessment App.

Scoring model is a simple, transparent weighted checklist designed for community
screening/awareness use only. It is NOT a clinical diagnostic tool -- see the
disclaimer text surfaced alongside every result in app.py.

Two rules deliberately sit *outside* the additive score, because a pure sum
mis-triages the cases that matter most:

1. Symptom escalation (see ARSENIC_SYMPTOM_FLOOR / ARSENIC_SPECIFIC_SYMPTOMS).
   Skin lesions and peripheral numbness are the two signs most specific to chronic
   arsenicosis, but the additive score under-rates them badly: skin lesions alone
   reach 25 and numbness alone 20, both inside the "low" band. Left as a pure sum,
   the questionnaire would hand a green all-clear to someone reporting the single
   most telling sign of the condition it screens for. So each of those symptoms
   floors the level at "medium" on its own, and the pair -- the classic
   presentation, still only 40 additively -- floors it at "high".
2. Urgency vs. emergency (see RiskResult.has_symptoms). A high score driven purely
   by exposure, with no symptoms reported, is a "get tested" situation, not an
   ambulance call. app.py uses this flag to decide whether to lead with 1669
   (emergency medical dispatch) or 1422 (disease-control surveillance).

Unknown option labels raise ValueError rather than scoring 0. Silently treating an
unrecognised answer as "no risk" is the wrong failure direction for a health tool.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# Districts along/near the Kok River basin covered by this MVP.
# NOTE: Mae Ai is administratively in Chiang Mai province but sits on the
# Kok/Fang river system upstream of Chiang Rai and is commonly included in
# Kok River contamination coverage -- kept per project scope.
#
# "hotline_key" links a district to its local hospital in EMERGENCY_HOTLINES so
# the nearest facility can be surfaced first. It does NOT affect the risk score.
DISTRICTS: dict[str, dict] = {
    "แม่อาย (Mae Ai)": {
        "lat": 19.9367,
        "lon": 99.3742,
        "name_th": "แม่อาย",
        "name_en": "Mae Ai",
        "hotline_key": "hosp_mae_ai",
    },
    "เมืองเชียงราย (Muang Chiang Rai)": {
        "lat": 19.9105,
        "lon": 99.8406,
        "name_th": "เมืองเชียงราย",
        "name_en": "Muang Chiang Rai",
        "hotline_key": "hosp_chiangrai_prachanukroh",
    },
    "เวียงชัย (Wiang Chai)": {
        "lat": 19.9667,
        "lon": 99.8667,
        "name_th": "เวียงชัย",
        "name_en": "Wiang Chai",
        "hotline_key": "hosp_wiang_chai",
    },
    "เชียงแสน (Chiang Saen)": {
        "lat": 20.2742,
        "lon": 100.0875,
        "name_th": "เชียงแสน",
        "name_en": "Chiang Saen",
        "hotline_key": "hosp_chiang_saen",
    },
}

# Water source usage checklist -> risk weight per selection.
WATER_USES: dict[str, int] = {
    "ดื่มน้ำจากแม่น้ำ/แหล่งน้ำใกล้แม่น้ำโดยตรง (ไม่ผ่านการกรอง/ต้ม)": 20,
    "ใช้ทำอาหาร": 10,
    "ใช้ในการเกษตร/รดน้ำพืชผัก": 5,
}

# Fish consumption frequency -> risk weight.
FISH_FREQUENCY: dict[str, int] = {
    "ไม่กินปลาจากแม่น้ำกกเลย": 0,
    "นาน ๆ ครั้ง (1-2 ครั้ง/เดือน)": 5,
    "บางครั้ง (1-2 ครั้ง/สัปดาห์)": 10,
    "บ่อยครั้ง (3-5 ครั้ง/สัปดาห์)": 15,
    "ทุกวัน": 20,
}

# Symptom checklist -> risk weight. Skin lesions and numbness are weighted
# higher as they are more specific indicators associated with heavy-metal
# (arsenic/lead) exposure in public health literature.
SYMPTOMS: dict[str, int] = {
    "ผื่น จุดด่างดำ หรือแผลผิดปกติที่ผิวหนัง": 20,
    "อาการชาหรือรู้สึกซ่าที่มือ/เท้า": 15,
    "อ่อนเพลียเรื้อรัง ไม่มีแรง แม้พักผ่อนเพียงพอ": 10,
    "ปวดท้อง คลื่นไส้ หรือท้องเสียบ่อยผิดปกติ": 5,
    "ปวดข้อ ปวดกล้ามเนื้อ โดยไม่ทราบสาเหตุ": 5,
}

# Minimum risk level each arsenic-specific symptom warrants ON ITS OWN, whatever
# the additive total says. Arsenical keratosis/hyperpigmentation and peripheral
# neuropathy are the hallmark signs of chronic exposure; reporting either one is
# grounds to get tested, so neither may ever come back green. See the module
# docstring for the arithmetic that makes this floor necessary.
ARSENIC_SYMPTOM_FLOOR: dict[str, str] = {
    "ผื่น จุดด่างดำ หรือแผลผิดปกติที่ผิวหนัง": "medium",
    "อาการชาหรือรู้สึกซ่าที่มือ/เท้า": "medium",
}

# The pair together is the classic chronic-arsenicosis presentation and escalates
# further, to "high" -- see calculate_risk_score.
ARSENIC_SPECIFIC_SYMPTOMS: frozenset[str] = frozenset(ARSENIC_SYMPTOM_FLOOR)

# Small, fixed baseline so every household along the river registers some
# non-zero exposure risk (all districts are within the affected basin).
#
# This baseline is deliberately UNIFORM across districts. Differentiating it
# would mean asserting that one district is more contaminated than another, and
# no public data supports such a ranking for the Kok basin. The district answer
# is therefore used only to surface the nearest hospital (see
# get_hotlines_for_district) -- never to change the score. Same principle as the
# omitted Wiang Chai phone number below: no data beats invented data.
LOCATION_BASELINE_SCORE = 5

RISK_THRESHOLDS = {
    "low": (0, 29),
    "medium": (30, 59),
    "high": (60, 10_000),
}

_LEVEL_PRESENTATION = {
    "low": ("ความเสี่ยงต่ำ", "green", "🟢"),
    "medium": ("ความเสี่ยงปานกลาง", "orange", "🟡"),
    "high": ("ความเสี่ยงสูง", "red", "🔴"),
}

# Ascending severity, so a floor can only ever raise a level, never lower it.
_LEVEL_ORDER = ("low", "medium", "high")


def _raise_to(current: str, floor: str) -> str:
    """Return whichever of the two levels is more severe."""
    return floor if _LEVEL_ORDER.index(floor) > _LEVEL_ORDER.index(current) else current


@dataclass
class RiskResult:
    score: int
    level: str  # "low" | "medium" | "high"
    label_th: str
    color: str
    emoji: str
    # True when the level was raised by the arsenic-specific symptom rule rather
    # than by the score alone. app.py explains this to the user -- the level is
    # never raised silently.
    escalated_by_symptoms: bool = False
    # Which hallmark symptoms triggered that escalation, so app.py can name them
    # instead of guessing which rule fired.
    escalating_symptoms: list[str] = field(default_factory=list)
    # True when the person reported at least one symptom. Drives the
    # emergency-vs-urgent split in the high-risk advice.
    has_symptoms: bool = False


def is_empty_submission(
    water_uses: list[str],
    fish_frequency: str,
    symptoms: list[str],
) -> bool:
    """True when the questionnaire carries no information to score.

    Every widget has a default, so a user can submit without answering anything.
    Scoring that produces the baseline 5 -> "low risk", i.e. a confident all-clear
    for someone who told us nothing. app.py refuses to render a verdict instead.
    """
    return not water_uses and not symptoms and FISH_FREQUENCY.get(fish_frequency, 0) == 0


def _validate_choices(values: list[str], allowed: dict[str, int], field: str) -> None:
    unknown = [v for v in values if v not in allowed]
    if unknown:
        raise ValueError(f"Unrecognised {field} option(s): {unknown!r}")


def calculate_risk_score(
    water_uses: list[str],
    fish_frequency: str,
    symptoms: list[str],
) -> RiskResult:
    """Compute a weighted risk score from questionnaire answers.

    Score = location baseline + sum(water use weights) + fish frequency weight
            + sum(symptom weights)

    The resulting level is then floored: each arsenic-specific symptom raises it to
    at least ARSENIC_SYMPTOM_FLOOR's value for that symptom, and reporting the full
    ARSENIC_SPECIFIC_SYMPTOMS pair raises it to "high". Floors only ever raise a
    level, so no combination of answers can talk the result back down.

    Raises:
        ValueError: if any answer is not a recognised option. Unknown answers are
            never silently scored as zero.
    """
    _validate_choices(water_uses, WATER_USES, "water use")
    _validate_choices([fish_frequency], FISH_FREQUENCY, "fish frequency")
    _validate_choices(symptoms, SYMPTOMS, "symptom")

    score = LOCATION_BASELINE_SCORE
    score += sum(WATER_USES[use] for use in water_uses)
    score += FISH_FREQUENCY[fish_frequency]
    score += sum(SYMPTOMS[symptom] for symptom in symptoms)

    if score <= RISK_THRESHOLDS["low"][1]:
        level = "low"
    elif score <= RISK_THRESHOLDS["medium"][1]:
        level = "medium"
    else:
        level = "high"

    band_level = level
    for symptom in symptoms:
        floor = ARSENIC_SYMPTOM_FLOOR.get(symptom)
        if floor is not None:
            level = _raise_to(level, floor)
    if ARSENIC_SPECIFIC_SYMPTOMS.issubset(symptoms):
        level = _raise_to(level, "high")

    escalated = level != band_level
    escalating = [s for s in symptoms if s in ARSENIC_SYMPTOM_FLOOR] if escalated else []

    label_th, color, emoji = _LEVEL_PRESENTATION[level]
    return RiskResult(
        score=score,
        level=level,
        label_th=label_th,
        color=color,
        emoji=emoji,
        escalated_by_symptoms=escalated,
        escalating_symptoms=escalating,
        has_symptoms=bool(symptoms),
    )


def get_recommendations(level: str, has_symptoms: bool = True) -> list[str]:
    """Return localized (Thai) actionable advice for a given risk level.

    At "high", the advice splits on whether any symptom was reported. A high score
    driven purely by exposure warrants prompt testing, not an emergency call --
    routing an asymptomatic person to 1669 (ambulance dispatch) is a false alarm.
    """
    if level == "low":
        return [
            "ยังคงเฝ้าระวังต่อเนื่อง หลีกเลี่ยงการดื่มน้ำจากแม่น้ำกกโดยตรงหากไม่มั่นใจในคุณภาพน้ำ",
            "ควรต้มน้ำหรือใช้เครื่องกรองน้ำก่อนบริโภคเสมอ",
            "สังเกตอาการผิดปกติของร่างกายอย่างสม่ำเสมอ และมาประเมินซ้ำทุก 1-2 เดือน",
            "ล้างมือ ล้างผัก/ผลไม้ที่ปลูกใกล้แม่น้ำให้สะอาดก่อนรับประทาน",
        ]
    if level == "medium":
        return [
            "ลดการสัมผัสน้ำจากแม่น้ำกกโดยตรง ทั้งการดื่มและการใช้ทำอาหาร เปลี่ยนไปใช้น้ำประปาหรือน้ำบรรจุขวดแทนหากเป็นไปได้",
            "ลดความถี่ในการบริโภคปลาที่จับจากแม่น้ำกก",
            "แจ้งอาการที่พบให้อาสาสมัครสาธารณสุขประจำหมู่บ้าน (อสม.) หรือเจ้าหน้าที่สาธารณสุขในพื้นที่ทราบ",
            "ควรไปรับการตรวจสุขภาพและตรวจระดับโลหะหนักในเลือด/ปัสสาวะที่โรงพยาบาลใกล้บ้านภายใน 2-4 สัปดาห์",
        ]
    if has_symptoms:
        return [
            "หยุดดื่มและหยุดใช้น้ำจากแม่น้ำกกในการทำอาหารทันที เปลี่ยนเป็นน้ำดื่มบรรจุขวดหรือน้ำประปาที่ตรวจสอบคุณภาพแล้ว",
            "งดรับประทานปลาและสัตว์น้ำที่จับจากแม่น้ำกกจนกว่าจะมีการยืนยันความปลอดภัยจากหน่วยงานสาธารณสุข",
            "ติดต่อโรงพยาบาลหรือหน่วยงานสาธารณสุขตามเบอร์ด้านล่างโดยเร็วที่สุด เพื่อตรวจคัดกรองสารโลหะหนัก",
            "แจ้ง อสม. หรือผู้นำชุมชนในพื้นที่ทันที เพื่อประสานการตรวจสอบคุณภาพน้ำและสุขภาพของครัวเรือนใกล้เคียง",
        ]
    # High exposure, no symptoms reported: act promptly, but this is not an
    # emergency. Deliberately avoids "ทันที/โดยเร็วที่สุด" and the ambulance line.
    return [
        "ท่านยังไม่มีอาการ แต่ระดับการสัมผัสสารปนเปื้อนอยู่ในเกณฑ์สูง จึงควรลดการสัมผัสและเข้ารับการตรวจคัดกรอง",
        "เปลี่ยนไปใช้น้ำดื่มบรรจุขวดหรือน้ำประปาที่ตรวจสอบคุณภาพแล้ว สำหรับการดื่มและการทำอาหาร",
        "ลดหรืองดการรับประทานปลาและสัตว์น้ำที่จับจากแม่น้ำกก จนกว่าจะมีการยืนยันความปลอดภัยจากหน่วยงานสาธารณสุข",
        "ติดต่อสายด่วน 1422 (กรมควบคุมโรค) หรือโรงพยาบาลใกล้บ้านตามเบอร์ด้านล่าง เพื่อขอรับการตรวจระดับโลหะหนักภายใน 1-2 สัปดาห์",
        "แจ้ง อสม. หรือผู้นำชุมชน เพื่อให้ครัวเรือนใกล้เคียงที่ใช้น้ำแหล่งเดียวกันได้รับการตรวจด้วย",
        "หากเริ่มมีอาการผิดปกติ เช่น ผื่น/แผลที่ผิวหนัง หรือมือเท้าชา ให้ติดต่อเจ้าหน้าที่สาธารณสุขทันที",
    ]


# ---------------------------------------------------------------------------
# Emergency hotlines (Chiang Rai / national) -- surfaced in the High-risk alert.
#
# Verified 2026-07-25 via web research against government/hospital-directory
# sources (NIEMS, DDC, Regional Health Office 1, healthserv.net hospital
# directory). See notes per entry. No dedicated Kok River arsenic-crisis
# hotline exists as of this date -- 1422 (Dept. of Disease Control) is the
# correct, real line actively used for arsenic-exposure health surveillance
# in the affected districts, so it is used instead of inventing one.
#
# Wiang Chai hospital's phone number is DELIBERATELY OMITTED: three
# independent directories give three different numbers for it
# (053-603-123 / 053-603-131 / 0-5376-8750-4) and the hospital's own site
# could not be reached to confirm. A wrong ER number is worse than none --
# Wiang Chai residents are routed to 1669/1422 instead. Confirm by phone
# with the hospital (โรงพยาบาลสมเด็จพระญาณสังวร) before adding a direct line.
# ---------------------------------------------------------------------------

# "key" is a stable identifier used for ordering/filtering (see
# get_hotlines_for_district) so display text can be edited without breaking logic.
# "emergency_only": entries that are only appropriate when someone is actually
# symptomatic -- 1669 dispatches ambulances and 191 is the police line. They are
# withheld from the asymptomatic high-exposure path.
EMERGENCY_HOTLINES: list[dict] = [
    {
        "key": "ems_1669",
        "name": "สายด่วนการแพทย์ฉุกเฉิน (National Emergency Medical Services)",
        "phone": "1669",
        "note": "โทรฟรี 24 ชั่วโมง สำหรับเหตุฉุกเฉินทางการแพทย์ทุกกรณี",
        "emergency_only": True,
    },
    {
        "key": "ddc_1422",
        "name": "สายด่วนกรมควบคุมโรค (Department of Disease Control Hotline)",
        "phone": "1422",
        "note": "สายด่วน 24 ชั่วโมง ใช้ติดตามและให้คำปรึกษาด้านสุขภาพจากการปนเปื้อนสารหนูในลุ่มน้ำกกโดยเฉพาะ",
        "emergency_only": False,
    },
    {
        "key": "pho_chiang_rai",
        "name": "สำนักงานสาธารณสุขจังหวัดเชียงราย (Chiang Rai Provincial Public Health Office)",
        "phone": "053-910-300",
        "note": "ประสานงานด้านสาธารณสุขระดับจังหวัด",
        "emergency_only": False,
    },
    {
        "key": "hosp_chiangrai_prachanukroh",
        "name": "โรงพยาบาลเชียงรายประชานุเคราะห์ (Chiangrai Prachanukroh Hospital)",
        "phone": "053-910-600",
        "note": "โรงพยาบาลศูนย์ประจำจังหวัด ครอบคลุมอำเภอเมืองเชียงราย รับส่งต่อผู้ป่วยจากทุกอำเภอ (เบอร์มือถือสำรอง 080-125-5555)",
        "emergency_only": False,
    },
    {
        "key": "hosp_mae_ai",
        "name": "โรงพยาบาลแม่อาย (Mae Ai Hospital, จังหวัดเชียงใหม่)",
        "phone": "053-459-036",
        "note": "โรงพยาบาลชุมชนประจำอำเภอแม่อาย (หมายเหตุ: อำเภอแม่อายอยู่ในเขตจังหวัดเชียงใหม่ ต้นน้ำของแม่น้ำกก)",
        "emergency_only": False,
    },
    {
        "key": "hosp_chiang_saen",
        "name": "โรงพยาบาลเชียงแสน (Chiang Saen Hospital)",
        "phone": "053-777-035",
        "note": "โรงพยาบาลชุมชนประจำอำเภอเชียงแสน (กด 121 เพื่อต่อสายตรงถึงห้องฉุกเฉิน)",
        "emergency_only": False,
    },
    {
        "key": "hosp_wiang_chai",
        "name": "โรงพยาบาลสมเด็จพระญาณสังวร (อำเภอเวียงชัย)",
        "phone": "-",
        "note": "เบอร์โทรตรงยังไม่สามารถยืนยันได้แน่ชัด กรุณาใช้สายด่วน 1669 หรือ 1422 แทนในกรณีฉุกเฉิน",
        "emergency_only": False,
    },
    {
        "key": "police_191",
        "name": "สายด่วนตำรวจ (Police Emergency)",
        "phone": "191",
        "note": "แจ้งเหตุด่วนเหตุร้ายทั่วไป",
        "emergency_only": True,
    },
]


def get_hotlines_for_district(district: str, has_symptoms: bool) -> list[dict]:
    """Order the hotline list for one district and one urgency situation.

    Symptomatic: 1669 first (emergency medical dispatch), then the district's own
    hospital, then everything else.

    Asymptomatic high exposure: emergency-only lines are removed entirely and 1422
    (disease-control surveillance) leads, followed by the district's own hospital.
    Calling an ambulance because you drink river water is a false alarm.

    Unknown districts degrade gracefully to the national lines rather than raising --
    this runs on the high-risk display path and must not be able to break it.
    """
    hotlines = [h for h in EMERGENCY_HOTLINES if has_symptoms or not h["emergency_only"]]
    local_key = DISTRICTS.get(district, {}).get("hotline_key")
    lead_key = "ems_1669" if has_symptoms else "ddc_1422"

    def sort_rank(hotline: dict) -> int:
        if hotline["key"] == lead_key:
            return 0
        if hotline["key"] == local_key:
            return 1
        return 2

    return sorted(hotlines, key=sort_rank)


HOTLINE_DISCLAIMER = (
    "เบอร์โทรศัพท์ข้างต้นเป็นเบอร์สลับสายหลักของแต่ละหน่วยงาน ตรวจสอบล่าสุดเมื่อ 25 กรกฎาคม 2569 และอาจมีการเปลี่ยนแปลงได้ "
    "หากติดต่อไม่ได้ กรุณาโทร 1669 (การแพทย์ฉุกเฉิน) หรือ 1422 (กรมควบคุมโรค) ซึ่งเป็นสายด่วนระดับประเทศที่พร้อมให้บริการตลอด 24 ชั่วโมง"
)


# ---------------------------------------------------------------------------
# Mock data for the Community Leader / อสม. dashboard
# ---------------------------------------------------------------------------

# ttl rather than a permanent cache: generate_mock_symptom_trend() is anchored on
# date.today(), so an indefinitely cached result would freeze the date labels on a
# long-running server.
_MOCK_CACHE_TTL_SECONDS = 3600


@st.cache_data(ttl=_MOCK_CACHE_TTL_SECONDS)
def generate_mock_district_risk() -> pd.DataFrame:
    """Mock % of surveyed population at Medium/High risk, per district.

    Clearly simulated data for MVP demo purposes -- not derived from real
    survey submissions.

    The three percentages are guaranteed to sum to exactly 100.0: high and medium
    are rounded first and low is derived from the rounded values. Rounding all
    three independently let the stacked bar total 100.1%.
    """
    rng = np.random.default_rng(seed=42)
    rows = []
    for district in DISTRICTS:
        high_pct = round(rng.uniform(8, 35), 1)
        medium_pct = round(rng.uniform(20, 45), 1)
        low_pct = round(max(0.0, 100 - high_pct - medium_pct), 1)
        rows.append(
            {
                "district": district,
                "ความเสี่ยงสูง (%)": high_pct,
                "ความเสี่ยงปานกลาง (%)": medium_pct,
                "ความเสี่ยงต่ำ (%)": low_pct,
            }
        )
    return pd.DataFrame(rows)


@st.cache_data(ttl=_MOCK_CACHE_TTL_SECONDS)
def generate_mock_symptom_trend(weeks: int = 12) -> pd.DataFrame:
    """Mock weekly time-series of reported symptom cases across all districts.

    Raises:
        ValueError: if weeks < 1. Zero produced an empty frame and a silently blank
            chart; negative raised an opaque error from inside numpy.
    """
    if weeks < 1:
        raise ValueError(f"weeks must be >= 1, got {weeks}")

    rng = np.random.default_rng(seed=7)
    today = _dt.date.today()
    start = today - _dt.timedelta(weeks=weeks - 1)
    dates = [start + _dt.timedelta(weeks=i) for i in range(weeks)]

    base_trend = np.linspace(12, 34, weeks)
    noise = rng.normal(0, 3, weeks)
    reports = np.clip(base_trend + noise, 0, None).round().astype(int)

    return pd.DataFrame({"สัปดาห์ (Week starting)": dates, "จำนวนรายงานอาการ": reports})


@st.cache_data(ttl=_MOCK_CACHE_TTL_SECONDS)
def generate_mock_map_points(points_per_district: int = 6) -> pd.DataFrame:
    """Mock geo-scattered risk markers around each district center for the map.

    Raises:
        ValueError: if points_per_district < 1. An empty frame has no lat/lon
            columns, which fails inside plotly rather than here.
    """
    if points_per_district < 1:
        raise ValueError(f"points_per_district must be >= 1, got {points_per_district}")

    rng = np.random.default_rng(seed=99)
    rows = []
    for district, coords in DISTRICTS.items():
        for _ in range(points_per_district):
            lat_jitter = rng.uniform(-0.05, 0.05)
            lon_jitter = rng.uniform(-0.05, 0.05)
            risk_level = rng.choice(["ต่ำ", "ปานกลาง", "สูง"], p=[0.5, 0.33, 0.17])
            rows.append(
                {
                    "district": district,
                    "lat": coords["lat"] + lat_jitter,
                    "lon": coords["lon"] + lon_jitter,
                    "risk_level": risk_level,
                }
            )
    return pd.DataFrame(rows)
