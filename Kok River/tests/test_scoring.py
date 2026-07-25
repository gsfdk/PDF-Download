"""Regression tests for the risk-scoring model.

These pin the *behaviour that protects users*, not the arithmetic. Weights and
thresholds are expected to change as real data arrives; what must not change is
that a hallmark symptom can never come back green, that an untouched form is
never scored as an all-clear, and that an unrecognised answer is never treated
as zero risk.

Run:  ./venv/bin/python -m pytest -v
"""

import pytest

import utils

NO_FISH = "ไม่กินปลาจากแม่น้ำกกเลย"
DAILY_FISH = "ทุกวัน"
SKIN_LESIONS = "ผื่น จุดด่างดำ หรือแผลผิดปกติที่ผิวหนัง"
NUMBNESS = "อาการชาหรือรู้สึกซ่าที่มือ/เท้า"
FATIGUE = "อ่อนเพลียเรื้อรัง ไม่มีแรง แม้พักผ่อนเพียงพอ"
DRINK_RAW = "ดื่มน้ำจากแม่น้ำ/แหล่งน้ำใกล้แม่น้ำโดยตรง (ไม่ผ่านการกรอง/ต้ม)"


def score(water=(), fish=NO_FISH, symptoms=()):
    return utils.calculate_risk_score(
        water_uses=list(water), fish_frequency=fish, symptoms=list(symptoms)
    )


# ---------------------------------------------------------------------------
# Hallmark symptoms must never return green
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("symptom", sorted(utils.ARSENIC_SYMPTOM_FLOOR))
def test_hallmark_symptom_alone_is_never_low(symptom):
    """Additively these land in the "low" band (25 and 20 against a 29 ceiling).

    Returning green to someone reporting the most arsenic-specific sign there is
    would be the worst failure this tool can produce, so a floor overrides the sum.
    """
    result = score(symptoms=[symptom])
    assert result.level != "low"
    assert result.escalated_by_symptoms is True
    assert symptom in result.escalating_symptoms


def test_both_hallmark_symptoms_escalate_to_high():
    """The classic chronic-arsenicosis presentation, worth only 40 additively."""
    result = score(symptoms=[SKIN_LESIONS, NUMBNESS])
    assert result.level == "high"
    assert result.escalated_by_symptoms is True


def test_escalation_flag_is_false_when_score_alone_decides():
    """The flag drives a UI explanation, so it must not fire spuriously.

    5 baseline + 20 raw water + 20 daily fish = 45, i.e. "medium" on the sum alone
    with no hallmark symptom involved.
    """
    result = score(water=[DRINK_RAW], fish=DAILY_FISH)
    assert result.level == "medium"
    assert result.escalated_by_symptoms is False
    assert result.escalating_symptoms == []


def test_floor_never_lowers_a_level():
    """A "medium" floor must not pull a high-scoring result back down."""
    result = score(
        water=list(utils.WATER_USES), fish=DAILY_FISH, symptoms=[SKIN_LESIONS]
    )
    assert result.level == "high"


# ---------------------------------------------------------------------------
# Band boundaries
# ---------------------------------------------------------------------------

def test_untouched_form_scores_only_the_baseline():
    assert score().score == utils.LOCATION_BASELINE_SCORE


def test_empty_submission_is_detected():
    """app.py refuses to render a verdict for this rather than showing green."""
    assert utils.is_empty_submission([], NO_FISH, []) is True


@pytest.mark.parametrize(
    "water,fish,symptoms",
    [
        ([], NO_FISH, [FATIGUE]),
        ([DRINK_RAW], NO_FISH, []),
    ],
)
def test_any_real_answer_is_not_an_empty_submission(water, fish, symptoms):
    assert utils.is_empty_submission(water, fish, symptoms) is False


def test_band_boundaries_hold():
    """29/30 and 59/60 are the low|medium and medium|high edges."""
    assert utils.RISK_THRESHOLDS["low"][1] == 29
    assert utils.RISK_THRESHOLDS["medium"][1] == 59
    # 5 baseline + 20 raw water + 5 fatigue = 30 -> first point of "medium"
    assert score(water=[DRINK_RAW], symptoms=[FATIGUE]).level == "medium"


def test_exposure_without_symptoms_is_high_but_flagged_asymptomatic():
    """Drives the screening-vs-emergency split: no symptoms, no ambulance line."""
    result = score(water=list(utils.WATER_USES), fish=DAILY_FISH)
    assert result.level == "high"
    assert result.has_symptoms is False


def test_maximum_input_is_high():
    result = score(
        water=list(utils.WATER_USES), fish=DAILY_FISH, symptoms=list(utils.SYMPTOMS)
    )
    assert result.level == "high"


# ---------------------------------------------------------------------------
# Unknown answers fail loudly
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        {"water_uses": ["ไม่มีตัวเลือกนี้"]},
        {"fish_frequency": "ไม่มีตัวเลือกนี้"},
        {"symptoms": ["ไม่มีตัวเลือกนี้"]},
    ],
)
def test_unknown_option_raises_rather_than_scoring_zero(kwargs):
    """Silently scoring an unrecognised answer as 0 fails in the unsafe direction."""
    call = {"water_uses": [], "fish_frequency": NO_FISH, "symptoms": [], **kwargs}
    with pytest.raises(ValueError):
        utils.calculate_risk_score(**call)


# ---------------------------------------------------------------------------
# Reference-data integrity
# ---------------------------------------------------------------------------

def test_hallmark_symptoms_exist_in_the_symptom_checklist():
    """Guards against a typo silently disabling the escalation rule."""
    assert set(utils.ARSENIC_SYMPTOM_FLOOR) <= set(utils.SYMPTOMS)


def test_hallmark_floors_are_real_levels():
    assert set(utils.ARSENIC_SYMPTOM_FLOOR.values()) <= set(utils.RISK_THRESHOLDS)


def test_every_hotline_has_the_fields_the_ui_reads():
    for hotline in utils.EMERGENCY_HOTLINES:
        assert {"name", "phone", "note"} <= hotline.keys()
        assert hotline["name"].strip()
        assert hotline["note"].strip()


def test_unverified_hotlines_use_the_sentinel_and_redirect():
    """A wrong ER number is worse than none -- unconfirmed lines say where to call."""
    for hotline in utils.EMERGENCY_HOTLINES:
        if hotline["phone"] == "-":
            assert "1669" in hotline["note"] or "1422" in hotline["note"]


def test_every_district_maps_to_a_real_hotline_entry():
    keys = {h.get("key") for h in utils.EMERGENCY_HOTLINES}
    for district, meta in utils.DISTRICTS.items():
        assert meta["hotline_key"] in keys, district


@pytest.mark.parametrize("district", sorted(utils.DISTRICTS))
@pytest.mark.parametrize("has_symptoms", [True, False])
def test_district_routing_always_returns_something_to_call(district, has_symptoms):
    hotlines = utils.get_hotlines_for_district(district, has_symptoms=has_symptoms)
    assert hotlines
    assert any(h["phone"] != "-" for h in hotlines), "no reachable number offered"


def test_district_choice_does_not_change_the_score():
    """District drives hospital routing only. Encoding a contamination gradient
    would assert a ranking no public Kok basin data supports."""
    assert utils.LOCATION_BASELINE_SCORE == 5
    assert all("weight" not in meta for meta in utils.DISTRICTS.values())


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def test_dates_come_from_thailand_not_the_server_clock(monkeypatch):
    """Streamlit Cloud runs UTC, 7 hours behind ICT. Between 00:00 and 07:00 Thai
    time a server-clock date is yesterday's, so every 'week starting' label on the
    dashboard would sit a day off for the users this tool exists for."""
    import datetime as dt

    # 02:00 in Bangkok on 26 Jul == 19:00 UTC on 25 Jul: the dates disagree.
    instant = dt.datetime(2026, 7, 26, 2, 0, tzinfo=utils.PROJECT_TZ)

    class FrozenDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    monkeypatch.setattr(utils._dt, "datetime", FrozenDatetime)

    assert utils.today_in_thailand() == dt.date(2026, 7, 26)
    assert instant.astimezone(dt.timezone.utc).date() == dt.date(2026, 7, 25)


def test_trend_ends_on_todays_thai_date():
    trend = utils.generate_mock_symptom_trend.__wrapped__(weeks=4)
    assert trend.iloc[-1, 0] == utils.today_in_thailand()
