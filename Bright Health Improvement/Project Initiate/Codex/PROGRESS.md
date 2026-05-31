# PROGRESS.md — Handoff State

> Source of truth for "who has the baton, what's next."
> Every session ends by updating the Active baton block + appending one Log row.

---

## Active baton

```
NEXT:      Manually run eveningCheckin(), reply in LINE, confirm the Sheet merge, then run
           eveningCheckinReminder() and confirm it skips
OWNER:     tan + either
BLOCKERS:  Tan must run the live evening prompt/reply/reminder verification
UPDATED:   2026-05-31 Asia/Bangkok
```

---

## Log

| When | Agent | What landed | Next handoff |
|---|---|---|---|
| 2026-05-30 | claude | Drafted SELF-LEARNING-PLAN.md (Phase A + B spec, 8 design principles, architecture diagram, schema, verification). Created Codex/ workspace scaffold (AGENTS.md, PROGRESS.md, SELF-LEARNING-PLAN.md). | codex: implement Phase A — Steps 1–4 of the spec. |
| 2026-05-30 | codex | Completed local Phase A implementation: Sheets scope, structured capture constants, extraction, locked daily Sheet upsert, context summary support, self-test, capture tail, context injection, and trigger setup. Static parse + manifest checks passed. | either: restore clasp access, configure SHEET_ID, deploy, and run live verification. |
| 2026-05-30 | codex | Restored private clasp binding, enabled CLI auth, preserved web-app manifest settings, pushed Apps Script, and redeployed the existing LINE webhook deployment in place as version 2. Created `Bright Health Daily Log` and bootstrapped `daily_log` headers. | tan + either: add SHEET_ID, approve Sheets scope, run editor self-test, and verify one LINE message. |
| 2026-05-30 | codex | Added public editor wrappers `setupSheet()` and `runSelfTest()` because Apps Script hides trailing-underscore helper functions from the Run dropdown. Redeployed the existing webhook in place as version 3. | tan + either: add SHEET_ID, refresh editor, run `setupSheet` + `runSelfTest`, and verify one LINE message. |
| 2026-05-30 | codex | Tan configured `SHEET_ID`, approved Sheets OAuth, and ran public `setupSheet()` successfully. Connector readback confirmed `daily_log!A1:I1` headers. First `runSelfTest()` reached Gemini extraction but failed on a transient Gemini quota/retry response before Sheet upsert assertions. | either: rerun `runSelfTest()` after quota clears; if repeatable, add bounded retry handling for Gemini 429 responses; then verify one real LINE message. |
| 2026-05-30 | codex | Added bounded Gemini 429 retry handling and a narrow regex extraction fallback for Phase A capture/self-test resilience under free-tier throttling. Redeployed the existing webhook in place as version 4. | either: rerun `runSelfTest()` on version 4, then verify one real LINE message lands in `daily_log`. |
| 2026-05-31 | codex | Fixed the regex fallback to reuse the same `SANITY_BOUNDS` sanitizer as Gemini JSON output after `runSelfTest()` correctly exposed that fallback accepted absurd weight `750`. Redeployed the existing webhook in place as version 5. | either: rerun `runSelfTest()` on version 5, then verify one real LINE message lands in `daily_log`. |
| 2026-05-31 | codex | Migrated the obsolete `gemini-2.0-flash` target to `gemini-3-flash-preview`. Split editor verification: public `runSelfTest()` now covers Phase A capture only; new public `runContextSelfTest()` covers the dormant Phase B Gemini summary path with row/property cleanup. Redeployed the existing webhook in place as version 6. | either: run `runSelfTest()` on version 6 and verify one real LINE capture; run `runContextSelfTest()` only before Phase B activation. |
| 2026-05-31 | codex | Confirmed the real LINE webhook and structured Sheet capture work, then replaced preview Gemini with stable `gemini-2.5-flash-lite`. Added bounded 5-second retries, sanitized `LAST_GEMINI_ERROR` diagnostics, shared response validation, and public `runGeminiSmokeTest()`. Redeployed the existing webhook in place as version 7. | tan + either: run `runGeminiSmokeTest()`, send one Thai LINE verification message, then begin the 3–5 day Phase A soak if replies are stable. |
| 2026-05-31 | tan | Ran public `runGeminiSmokeTest()` on version 7 successfully: `model=gemini-2.5-flash-lite response=OK`. | tan + either: send one Thai LINE verification message and confirm a normal reply before starting the Phase A soak. |
| 2026-05-31 | tan + codex | Completed version 7 live LINE verification: normal Thai coaching reply returned, and connector readback confirmed one merged `daily_log` row with weight `74.5`, water `6`, exercise `30`, and the earlier mood note. | tan: begin the 3–5 day Phase A soak; spot-check captured values before Phase B activation. |
| 2026-05-31 | codex | Added Phase A.1 proactive capture: morning prompts now end with questions, evening check-in runs at 20:00, one unanswered reminder runs around 21:30, response state is stored in Script Properties, and public `runProactiveCheckinSelfTest()` validates reminder eligibility without LINE sends. Trigger setup now removes the dormant Phase B cron and clears `USER_CONTEXT`. Redeployed the existing webhook in place as version 8. | tan + either: run editor verification, manually exercise the evening prompt/reply/reminder flow, then restart the 3–5 day soak. |
| 2026-05-31 | tan | Ran `runProactiveCheckinSelfTest()` successfully and ran `setupTriggers()` successfully. Phase A.1 triggers are installed for 07:00, 20:00, and reminder around 21:30 Asia/Bangkok daily. | tan + either: manually run the evening prompt/reply/reminder flow and confirm the Sheet merge before restarting the soak. |

---

## Roadmap (project-level, beyond current Phase A/B)

- [x] Bot core: webhook + Gemini + LINE Reply/Push + Google Doc log + rolling history
- [x] Deployed v1 to Apps Script (May 28 2026)
- [ ] **CURRENT:** Phase A.1 — version 8 deployed; waiting on editor and live LINE verification before restarting the soak
- [ ] **NEXT:** Phase B — activate nightly summarizer → `USER_CONTEXT` injection after the soak
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
| 2026-05-31 | Stable `gemini-2.5-flash-lite` for LINE replies and extraction | Stable model with higher free-tier throughput is a better fit than preview quality for short Thai coaching messages |
| 2026-05-31 | Proactive Phase A.1 check-ins at 07:00, 20:00, and one unanswered reminder around 21:30 | Active prompts collect better soak data without repeatedly chasing the user or consuming Gemini quota |

---

## How to update this file (for either agent)

1. **At session end**, update the Active baton block:
   - `NEXT:` — the one-line task the next session will pick up
   - `OWNER:` — `claude`, `codex`, or `either`
   - `BLOCKERS:` — anything the next session needs from Tan before starting (else `none`)
   - `UPDATED:` — today's date + `Asia/Bangkok`
2. **Append exactly one row** to the Log table with what landed this session and the handoff intent.
3. Commit with prefix `[claude]` or `[codex]`. Push.
