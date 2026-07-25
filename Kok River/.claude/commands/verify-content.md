---
description: Re-verify Kok River hotlines and health advice against live sources
---

Verify the *content* of this app against reality. Code correctness is covered by
`./venv/bin/python -m pytest`; this command checks the facts that go stale.

Dispatch the `web-researcher` sub-agent. It must not have authored the data it is
checking — a model reviewing its own output is measurably too lenient, which is the
whole reason this runs as a separate agent rather than inline.

Ask it to check, against Thai government and hospital-directory sources:

1. **Every entry in `utils.EMERGENCY_HOTLINES`** — does the number still belong to the
   named organisation, and does the organisation still exist under that name? Flag any
   that have changed, and any that can no longer be confirmed at all.
2. **The Wiang Chai gap** — `โรงพยาบาลสมเด็จพระญาณสังวร` currently carries the `"-"`
   sentinel because three directories disagreed. Can a single number now be confirmed
   from an authoritative source (the hospital's own site, MOPH directory)? Report the
   sources, not just the number.
3. **1422's relevance** — is it still the line handling Kok basin arsenic surveillance,
   or has a dedicated line been established since?
4. **`utils.get_recommendations`** — does the Thai advice still match current MOPH / DDC
   guidance for suspected heavy-metal exposure, particularly the recommended testing
   window (currently 2–4 weeks at medium, 1–2 weeks at high-exposure-no-symptoms)?

Rules for this pass:

- **Report a diff. Never edit `utils.py` directly.** Hotline data is safety-critical and
  changes to it get a human read first.
- **Never propose a number sourced from a single unverified directory.** If sources
  disagree, the correct output is "still unconfirmed, keep the sentinel" — a wrong ER
  number is worse than none.
- Cite a source per finding.

Afterwards, update the re-verification date in `NOTES.md` and, if any number changed,
the `HOTLINE_DISCLAIMER` date string in `utils.py`.
