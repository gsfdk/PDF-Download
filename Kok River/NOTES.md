# Implementation notes — Kok River risk assessment

Running record of *why* things are the way they are, so future sessions don't
re-derive settled decisions or silently undo them. Newest section last.

---

## Decisions

**Mae Ai is in scope despite being in Chiang Mai province.** It sits on the Kok/Fang
system upstream of Chiang Rai and is routinely included in Kok contamination coverage.
Its hospital entry carries a note making the province explicit so nobody "corrects" it.

**1422 is used instead of a Kok-River-specific hotline.** As of 2026-07-25 no dedicated
arsenic-crisis line exists. 1422 (Dept. of Disease Control) is the real line used for
arsenic-exposure surveillance in the affected districts. Inventing a plausible-looking
crisis number would have been the easy path and the wrong one.

**Wiang Chai hospital has no direct number.** Three independent directories give three
different values (053-603-123 / 053-603-131 / 0-5376-8750-4) and the hospital's own site
could not be reached. Entry uses the `"-"` sentinel and redirects to 1669/1422. To
resolve: phone โรงพยาบาลสมเด็จพระญาณสังวร and confirm directly.

**District does not affect the score.** Only hospital routing. See CLAUDE.md rule 4.
Revisit only if per-location sampling data for the basin is published.

**Thresholds 30/60 are unvalidated.** They are a reasonable-looking split, not a
clinically derived one. No source backs them. This is the single biggest correctness
caveat in the tool and should be reviewed by a public health officer before any real
deployment.

---

## Edge cases found by probing the scorer (2026-07-25)

Fed deliberately adversarial inputs *before* building, rather than testing the happy
path afterwards. Four defects surfaced, all now fixed:

| Input | Was | Now |
|---|---|---|
| Blank form submitted | 5 → 🟢 low, a confident all-clear for someone who said nothing | `is_empty_submission` → app refuses to render a verdict |
| Skin lesions only | 25 → 🟢 low | floored to 🟡 medium, with the reason named |
| Numbness only | 20 → 🟢 low | floored to 🟡 medium, with the reason named |
| Heavy exposure, no symptoms | 🔴 high with 🚨 + 1669/191 ambulance framing | still high, but screening copy and 1422/provincial lines |

The first two were the serious ones: the questionnaire handed a green all-clear to
someone reporting the most arsenic-specific sign it asks about.

An earlier iteration escalated only when **both** hallmark symptoms were present
(`issubset`). That catches a case the additive score already rated medium while missing
the single-symptom case that motivated the rule. Now each symptom floors at medium
individually and the pair still escalates to high.

---

## Open unknowns

- **No persistence.** Tab 1 submissions vanish; the อสม. dashboard is permanently mock.
  This is the real MVP exit condition. It also pulls in **Thai PDPA** — district plus
  symptoms is health data, so consent, retention, and access have to be decided before
  the first real row is stored. Do not add a database without settling that first.
- **Thresholds unvalidated** (above).
- **Mobile untested.** The intended users are villagers and อสม. on phones;
  `layout="wide"` with two-column forms has never been checked on a small screen.
- **No offline story** for rural connectivity.
- **Hotlines need periodic re-verification.** Last verified 2026-07-25.
  **Re-verify by 2027-01-25** (6 months), or sooner after any local health-office
  reorganisation. Run `/verify-content`.
