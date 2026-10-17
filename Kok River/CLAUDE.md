# CLAUDE.md — Kok River Community Health Risk Assessment

Streamlit MVP that screens villagers and อสม. along the Kok River (Chiang Rai) for
health risk from transboundary mining contamination (arsenic/lead). All user-facing
text is Thai.

```bash
./venv/bin/streamlit run app.py       # run the app
./venv/bin/python -m pytest -q        # run the tests
```

`app.py` is presentation only. `utils.py` holds all scoring, reference data, and
hotlines. Dashboard data is mock — there is no persistence layer yet.

## Rules, and why they exist

These are the ones worth breaking a habit over. The reasoning matters more than the
rule, so if you find a better way to honour the reason, take it.

1. **Never invent, guess, or "best-guess" a phone number.** Contradictory sources mean
   the entry gets `"phone": "-"` plus a note redirecting to 1669/1422. A villager
   dialling a wrong ER number in a crisis is worse off than one who was told to call
   the national line. Precedent: the Wiang Chai hospital entry in `utils.py`.

2. **The questionnaire must never return 🟢 to someone reporting a hallmark sign.**
   Skin lesions and peripheral numbness are the signs most specific to chronic
   arsenicosis, and the additive score under-rates both. `ARSENIC_SYMPTOM_FLOOR`
   overrides the arithmetic. False reassurance is this tool's worst failure mode —
   worse than over-referral, because the person stops looking.

3. **Escalation is never silent.** If a floor raised the level, `app.py` names the
   symptom that did it. A user told "high risk" with no explanation cannot act on it,
   and an unexplained result reads as a malfunction.

4. **Don't encode precision the data doesn't support.** Every district shares one flat
   `LOCATION_BASELINE_SCORE`; district drives hospital routing only. Weighting by
   distance upstream would assert a contamination gradient no public Kok basin data
   establishes. Withhold rather than invent — same principle as rule 1.

5. **Never render mock data without a visible mock label.** อสม. may act on what they
   see, and simulated numbers presented plainly become real decisions.

6. **Unknown answers raise, never score 0.** An unrecognised option scored as "no risk"
   fails in the unsafe direction.

## Before changing scoring weights

Run the tests. They pin user-protecting behaviour, not arithmetic — if a weight change
breaks one, the fix is usually the weight, not the test. Thresholds (30/60) are **not**
clinically validated; see `NOTES.md`.
