# AGENTS.md — Codex workspace

> Codex's home base for the Bright Health LINE bot project.
> Read this first. Then `PROGRESS.md`. Then `SELF-LEARNING-PLAN.md`.

---

## Active work
**Phase A of the self-learning feature.** Full spec in `SELF-LEARNING-PLAN.md`.
Current baton owner & next task: see `PROGRESS.md` → "Active baton" block.

---

## Handoff protocol (two-agent: Claude ↔ Codex)

**Session start — every time:**
```bash
cat PROGRESS.md                # who has the baton, what's next, blockers
cat SELF-LEARNING-PLAN.md      # the frozen spec
git log --oneline -10          # what just landed
cd .. && clasp pull            # pull latest code from Apps Script cloud
```

**Session end — every time:**
```bash
cd ..                          # back to project root where .clasp.json lives
clasp push                     # if any .gs changed
# back to Codex/ to update docs
cd Codex
# Update PROGRESS.md: Active baton block + append one Log row
git add -A
git commit -m "[codex] <type>: <short summary>"   # see commit prefix rule below
git push
```

**Commit prefix rule:**
- Every commit starts with `[claude]` or `[codex]` so either agent (or human) can scan history and know who did what.
- Types: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`.
- Example: `[codex] feat: add extractHealthData_ + logToSheet_ for Phase A capture`

---

## Project location (where code actually lives)

The bot code is one level up from this folder:
```
Project Initiate/
├── HealthCoachBot.gs     ← Codex edits this for Phase A
├── appsscript.json       ← Codex edits this (add Sheets scope)
├── CLAUDE.md             ← project-level context (read for stack details)
├── PROGRESS.md (root)    ← legacy progress doc, do not modify
├── deployment-records/   ← deploy screenshots
└── Codex/                ← YOU ARE HERE
    ├── AGENTS.md             ← this file
    ├── PROGRESS.md           ← baton & log (the source of truth for handoff state)
    └── SELF-LEARNING-PLAN.md ← frozen spec for current work
```

**When editing .gs:** use relative paths like `../HealthCoachBot.gs`. `clasp` commands must be run from the project root (`cd ..` first) because that's where `.clasp.json` lives.

---

## Stack reference (read CLAUDE.md at `../CLAUDE.md` for full details)

| Layer | Tech | Notes |
|---|---|---|
| Host | Google Apps Script | free, no server, never sleeps |
| AI | Gemini 2.0 Flash (`gemini-2.0-flash`) | Google AI Studio free tier, 1,500 req/day |
| Messaging | LINE Messaging API | Reply + Push |
| Log (raw) | Google Doc (`LOG_DOC_ID`) | unchanged by this feature |
| Log (structured, NEW) | Google Sheet (`SHEET_ID`) | added in Phase A |
| Memory | Script Properties: `HISTORY` (rolling 8 turns), `USER_CONTEXT` (Phase B) | |

---

## Script Properties currently set (do NOT echo in commits or chat)
- `LINE_CHANNEL_ACCESS_TOKEN`
- `GEMINI_API_KEY`
- `LOG_DOC_ID`
- `LINE_USER_ID`
- `HISTORY`
- `LOG_LAST_DATE`

**To add for Phase A:**
- `SHEET_ID` — Google Sheet ID (manually create the Sheet first, paste the ID)

**To add for Phase B:**
- `USER_CONTEXT` — auto-written by `dailyContextUpdate()` cron, no manual setup

---

## Safety rules (non-negotiable)
1. **Secrets stay in Script Properties, never in code.** If you see a real token/key in chat or a file, treat it as compromised — tell the user to regenerate.
2. **Bot is a coach, not a doctor.** Never alter the medical guardrails in `SYSTEM_PROMPT`. No supplement/drug/diagnostic advice paths.
3. **Sheet failures must not break replies.** All capture logic wraps in `try/catch` and runs *after* `replyLine_()`.
4. **Never `git commit`** `.clasp.json`, `.env`, or anything with `token` / `secret` in the name.
5. **Never `--amend`** Claude's commits (or your own past commits). Always make a new commit.
6. **Never skip git hooks** (`--no-verify`).

---

## Quick test cheatsheet (after `clasp push`)

In the Apps Script editor:
1. Select `setupSheet_` from the function dropdown → Run → accept the new Sheets OAuth scope.
2. Select `runSelfTest_` → Run → check Executions log; all assertions should pass.
3. Send a real Thai LINE message → verify Sheet row + normal bot reply.

---

## Division of labor (suggested)
| Agent | Lean on for |
|---|---|
| **Claude Code** | architecture, prompt design, spec edits, multi-file refactors, MCP integrations |
| **Codex** | tight single-function implementation, `clasp push`/`pull` ops, line-level `.gs` edits |

If both want the same task, the Active baton block in `PROGRESS.md` decides — whoever's name is on it owns it until handoff.
