# PROGRESS.md — Handoff State

> Source of truth for "who has the baton, what's next."
> Every session ends by updating the Active baton block + appending one Log row.

---

## Active baton

```
NEXT:      Phase A activation — add SHEET_ID in Apps Script Project Settings, run setupSheet_
           + runSelfTest_ in the editor, then verify one real Thai LINE message
OWNER:     tan + either
BLOCKERS:  Tan must add SHEET_ID=1ISFE_GHj1DyNRLBohZHCks5MMn3lSZ2i5zZLbz4Y2N4 in Script Properties
           and approve the new Sheets OAuth scope when setupSheet_ runs
UPDATED:   2026-05-30 Asia/Bangkok
```

---

## Log

| When | Agent | What landed | Next handoff |
|---|---|---|---|
| 2026-05-30 | claude | Drafted SELF-LEARNING-PLAN.md (Phase A + B spec, 8 design principles, architecture diagram, schema, verification). Created Codex/ workspace scaffold (AGENTS.md, PROGRESS.md, SELF-LEARNING-PLAN.md). | codex: implement Phase A — Steps 1–4 of the spec. |
| 2026-05-30 | codex | Completed local Phase A implementation: Sheets scope, structured capture constants, extraction, locked daily Sheet upsert, context summary support, self-test, capture tail, context injection, and trigger setup. Static parse + manifest checks passed. | either: restore clasp access, configure SHEET_ID, deploy, and run live verification. |
| 2026-05-30 | codex | Restored private clasp binding, enabled CLI auth, preserved web-app manifest settings, pushed Apps Script, and redeployed the existing LINE webhook deployment in place as version 2. Created `Bright Health Daily Log` and bootstrapped `daily_log` headers. | tan + either: add SHEET_ID, approve Sheets scope, run editor self-test, and verify one LINE message. |

---

## Roadmap (project-level, beyond current Phase A/B)

- [x] Bot core: webhook + Gemini + LINE Reply/Push + Google Doc log + rolling history
- [x] Deployed v1 to Apps Script (May 28 2026)
- [ ] **CURRENT:** Phase A — version 2 deployed; activation blocked on owner-authorized `SHEET_ID` + editor self-test
- [ ] **NEXT:** Phase B — nightly summarizer → `USER_CONTEXT` injection
- [ ] Weekly progress chart from Sheet → LINE image
- [ ] Doctor appointment reminders
- [ ] Emergency symptom escalation
- [ ] LINE Rich Menu (quick buttons)

---

## Architecture decisions log
| When | Decision | Why |
|---|---|---|
| 2026-05 | Apps Script over Hermes/Flask | free, no server, never sleeps |
| 2026-05 | Gemini 2.0 Flash only (no provider switch) | free tier covers daily volume, simpler |
| 2026-05 | Single `.gs` file, constants at top | Apps Script flat-file model is fine; no premature splitting |
| 2026-05-30 | Phase A before Phase B, with 3–5 day soak | Phase B reads from the Sheet — bad inputs = bad summaries |
| 2026-05-30 | Daily 23:00 Bangkok for context cron (not weekly) | Weekly = stale up to 6 days; daily keeps coach reactive to mid-week patterns |
| 2026-05-30 | `LockService` on every Sheet upsert | LINE can deliver burst messages; we need race safety |
| 2026-05-30 | `source_message` column added to schema | Every number traceable back to the message that produced it |

---

## How to update this file (for either agent)

1. **At session end**, update the Active baton block:
   - `NEXT:` — the one-line task the next session will pick up
   - `OWNER:` — `claude`, `codex`, or `either`
   - `BLOCKERS:` — anything the next session needs from Tan before starting (else `none`)
   - `UPDATED:` — today's date + `Asia/Bangkok`
2. **Append exactly one row** to the Log table with what landed this session and the handoff intent.
3. Commit with prefix `[claude]` or `[codex]`. Push.
