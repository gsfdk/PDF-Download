"""Renders the real app.py and asserts what the user actually sees.

test_scoring.py proves the model is right; this proves the UI is wired to it. It
catches the class of bug where a guard exists in utils.py, is imported, and is
simply never reached -- which no amount of unit testing on the scorer would show.

Run:  ./venv/bin/python -m pytest -q
"""

import pytest
from streamlit.testing.v1 import AppTest

import utils

APP = str(__import__("pathlib").Path(__file__).parent.parent / "app.py")

SKIN = "ผื่น จุดด่างดำ หรือแผลผิดปกติที่ผิวหนัง"
NUMB = "อาการชาหรือรู้สึกซ่าที่มือ/เท้า"
FATIGUE = "อ่อนเพลียเรื้อรัง ไม่มีแรง แม้พักผ่อนเพียงพอ"
DAILY_FISH = "ทุกวัน"


def submit(water=(), fish=None, symptoms=()):
    """Fill the questionnaire and press the submit button."""
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    if water:
        at.multiselect[0].set_value(list(water))
    if fish:
        at.radio[0].set_value(fish)
    at.multiselect[1].set_value(list(symptoms))
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def rendered(at):
    parts = []
    for coll in (at.markdown, at.warning, at.error, at.info, at.success, at.metric):
        for el in coll:
            parts.append(str(getattr(el, "value", "")) + str(getattr(el, "label", "")))
    return "\n".join(parts)


def test_blank_submission_shows_no_verdict():
    at = submit(symptoms=[])
    assert "ความเสี่ยงต่ำ" not in rendered(at), "green all-clear shown for an empty form"
    assert at.warning, "no prompt shown asking the user to answer something"


@pytest.mark.parametrize("symptom", [SKIN, NUMB])
def test_single_hallmark_symptom_renders_medium_and_explains_itself(symptom):
    at = submit(symptoms=[symptom])
    body = rendered(at)
    assert "ความเสี่ยงปานกลาง" in body
    assert "ความเสี่ยงต่ำ" not in body
    reasons = [str(w.value) for w in at.warning if "เหตุผลที่ยกระดับ" in str(w.value)]
    assert reasons, "level was raised without telling the user why"
    assert any(symptom in r for r in reasons), "explanation does not name the symptom"


def test_both_hallmark_symptoms_render_high_with_pair_wording():
    at = submit(symptoms=[SKIN, NUMB])
    assert "ความเสี่ยงสูง" in rendered(at)
    assert any("ทั้ง" in str(w.value) for w in at.warning)


def test_exposure_without_symptoms_gets_screening_not_emergency():
    """No symptoms means no ambulance referral -- see CLAUDE.md rule on false alarms."""
    at = submit(water=list(utils.WATER_USES), fish=DAILY_FISH, symptoms=[])
    body = rendered(at)
    assert "ความเสี่ยงสูง" in body
    assert "1422" in body
    assert not at.error, "urgent red-alert framing used for an asymptomatic user"

    district = next(iter(utils.DISTRICTS))
    cards = [h["phone"] for h in utils.get_hotlines_for_district(district, has_symptoms=False)]
    assert cards[0] == "1422"
    # 1669/191 may still appear in HOTLINE_DISCLAIMER and the Wiang Chai redirect
    # note; those are fallbacks, not a referral. They must not be offered as cards.
    assert "1669" not in cards
    assert "191" not in cards


def test_symptomatic_high_risk_gets_the_emergency_line():
    at = submit(water=list(utils.WATER_USES), fish=DAILY_FISH, symptoms=[SKIN, NUMB, FATIGUE])
    assert "ความเสี่ยงสูง" in rendered(at)
    assert at.error, "no urgent framing for a symptomatic high-risk user"
    district = next(iter(utils.DISTRICTS))
    cards = [h["phone"] for h in utils.get_hotlines_for_district(district, has_symptoms=True)]
    assert cards[0] == "1669"


def test_dashboard_labels_its_data_as_mock():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert any("จำลอง" in str(i.value) for i in at.info), "mock data not labelled"
