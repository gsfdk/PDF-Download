# แอปประเมินความเสี่ยงสุขภาพชุมชน แม่น้ำกก

Kok River Community Health Risk Assessment — a Streamlit MVP that screens villagers and
อสม. (village health volunteers) along the Kok River, Chiang Rai, for health risk from
heavy-metal contamination (arsenic and lead) linked to transboundary mining.

All user-facing text is Thai. Districts covered: แม่อาย, เมืองเชียงราย, เวียงชัย, เชียงแสน.

> **This is a screening and awareness tool, not a diagnostic one.** It cannot replace a
> clinician or a laboratory test, and the app says so on every result.

## Quickstart

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/streamlit run app.py            # http://localhost:8501
```

Development:

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest -q             # 36 tests
```

Requires Streamlit 1.49+ and plotly 5.24+. Older versions install fine and then fail at
runtime on `width="stretch"` and `px.scatter_map` respectively, so the floors in
`requirements.txt` are deliberate.

## What's in the app

**Tab 1 — personal risk questionnaire.** District, water use, fish consumption, and
symptoms produce a weighted score and a low/medium/high verdict with Thai advice. High
risk also surfaces hotlines, ordered so the user's own district hospital is near the top.

**Tab 2 — อสม. / community leader dashboard.** Per-district risk breakdown, weekly
symptom trend, and a map. **All dashboard data is simulated** and labelled as such in the
UI. There is no persistence layer, so nothing submitted in Tab 1 feeds it.

## Layout

| File | Role |
|---|---|
| `app.py` | Presentation only — layout, widgets, rendering |
| `utils.py` | All scoring logic, reference data, and hotline numbers |
| `tests/test_scoring.py` | Scoring rules, escalation floors, hotline routing |
| `tests/test_app_render.py` | End-to-end render assertions against the real app |
| `CLAUDE.md` | Working rules for anyone (human or agent) editing this project |
| `NOTES.md` | Why decisions were made, plus open unknowns |

## The scoring model, and why it isn't just a sum

Score = location baseline (5, uniform) + water-use weights + fish-frequency weight +
symptom weights. Bands: 0–29 low, 30–59 medium, 60+ high.

Two rules sit deliberately **outside** that sum, because a pure total mis-triages the
cases that matter most:

1. **Hallmark symptom floors.** Skin lesions (20) and peripheral numbness (15) are the
   signs most specific to chronic arsenicosis, yet either one alone lands inside the
   "low" band. Left as arithmetic, the questionnaire would hand a green all-clear to
   someone reporting the single most telling sign of the condition it screens for. Each
   floors the level at medium on its own; the pair floors it at high.
2. **Urgency is not emergency.** A high score with no symptoms is an exposure problem,
   not a medical emergency. That path drops 1669 (ambulance dispatch) and 191 entirely
   and leads with 1422, the disease-control surveillance line.

Escalations are never silent — when a floor overrides the arithmetic, the app names the
symptom responsible.

Full reasoning in `CLAUDE.md`; decision history and open questions in `NOTES.md`.

## Known limitations

- **The 30/60 thresholds are not clinically validated.** They are a reasonable-looking
  split, not a derived one. This is the biggest correctness caveat in the tool and should
  be reviewed by a public health officer before any real deployment.
- **No persistence.** Submissions are not stored anywhere. Adding storage pulls in Thai
  **PDPA** obligations, since district plus symptoms is health data — consent, retention,
  and access must be settled before the first real row is written.
- **Mobile untested.** The intended users are on phones; the wide two-column layout has
  not been checked on a small screen.
- **Hotlines need periodic re-verification.** Last verified 2026-07-25; re-verify by
  2027-01-25. One number (โรงพยาบาลสมเด็จพระญาณสังวร, เวียงชัย) is deliberately absent
  because three directories disagree — a wrong emergency number is worse than none.
