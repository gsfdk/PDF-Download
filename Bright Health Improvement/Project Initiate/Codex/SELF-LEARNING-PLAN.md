# Self-Learning Spec — Capture → Recall

> Frozen spec. Do not modify without proposing the amendment in chat first.
> Code lives one level up: `../HealthCoachBot.gs`, `../appsscript.json`.

## Context
The bot has no behavioral memory. The Google Doc stores raw messages but is never read back, so the coach can't notice patterns (water habits, exercise streaks, weight trend). Without structured data, "personalized coaching" is theater.

**Goal — two-stage memory loop:**
- **Phase A — Capture.** Every inbound message → extract numbers → upsert one row per day into a Google Sheet.
- **Phase B — Recall.** Nightly cron summarizes the last 7 days from the Sheet → stores a short Thai paragraph in `USER_CONTEXT` → injected into every Gemini call so the coach's next reply reflects Bright's actual recent behavior.

Ship Phase A first, watch real data for 3–5 days, then ship Phase B once we trust the inputs.

---

## Design principles (non-negotiable)

1. **Failure-isolated.** Sheet writes and context summaries run *after* the LINE reply. Nothing on the data layer can break the user-visible reply path.
2. **Race-safe.** `LockService` wraps every Sheet upsert. Two LINE messages arriving in the same second won't overwrite each other.
3. **Self-bootstrapping.** No manual Sheet headers. `setupSheet_()` creates and validates structure idempotently on first run.
4. **Self-validating.** `runSelfTest_()` is one button: extraction, upsert, context summary, sanity bounds — all in one call.
5. **Sanity-bounded.** Gemini hallucinations (weight 750, water 99) are dropped silently per-field; other fields still land.
6. **Auditable.** Every Sheet row carries `source_message` (truncated user text) so we can always trace a number back to the message that produced it.
7. **One file.** All logic stays in `HealthCoachBot.gs`. Constants live at the top.
8. **Reversible.** Phase B only *reads* the Sheet. Disabling Phase B (delete one trigger, delete one property) instantly returns the bot to Phase A behavior. No data loss.

---

## End-state architecture

```
LINE inbound
   │
   ▼
doPost ─► handleMessage_
              │
              ├─► callGemini_(text, history) reads USER_CONTEXT inside
              ├─► replyLine_ ──► LINE
              ├─► logToDoc_ (raw conversation, unchanged)
              └─► extractHealthData_ ─► logToSheet_  (best-effort, locked)

[cron: daily 23:00 Asia/Bangkok]
   └─► dailyContextUpdate ─► summarizeContext_ ─► props.USER_CONTEXT
```

---

## Files touched

| File | Edit |
|---|---|
| `../HealthCoachBot.gs` | Add constants, 6 new functions, extend `handleMessage_`, `callGemini_`, `setupTriggers` |
| `../appsscript.json` | Add `spreadsheets` scope (4 total) |
| **No new files. No new packages.** | — |

---

## Step 1 — Manifest

`../appsscript.json`:
```json
{
  "timeZone": "Asia/Bangkok",
  "runtimeVersion": "V8",
  "exceptionLogging": "STACKDRIVER",
  "oauthScopes": [
    "https://www.googleapis.com/auth/script.external_request",
    "https://www.googleapis.com/auth/script.scriptapp",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets"
  ]
}
```

After `clasp push`, run any function once in the editor → accept the new Sheets scope.

---

## Step 2 — Constants block (top of `../HealthCoachBot.gs`)

```js
const SHEET_NAME = 'daily_log';
const SHEET_HEADERS = [
  'date', 'weight_kg', 'water_glasses', 'exercise_min',
  'sleep_hr', 'mood_1to5', 'note', 'source_message', 'updated_at'
];

// Drop any extracted value outside these bounds (hallucination guard).
const SANITY_BOUNDS = {
  weight_kg:     [40, 200],
  water_glasses: [0, 25],
  exercise_min:  [0, 300],
  sleep_hr:      [0, 15],
  mood_1to5:     [1, 5]
};

const CONTEXT_WINDOW_DAYS = 7;
const SOURCE_MSG_MAX_LEN  = 200;
```

One Script Property to add manually before deploy: `SHEET_ID` (create an empty Google Sheet, copy the ID from URL, paste into Apps Script Project Settings → Script Properties). Headers auto-generate on first run.

---

## Step 3 — New functions

### 3a. `setupSheet_()` — bootstrap (idempotent)
**Purpose:** Open the Sheet, ensure a tab named `daily_log` exists, ensure row 1 matches `SHEET_HEADERS`. Safe to call any number of times.

```js
function setupSheet_() // returns Sheet
```
Logic:
- Open by `SHEET_ID`.
- If tab `daily_log` missing → create it.
- If row 1 doesn't match `SHEET_HEADERS` exactly → overwrite row 1 with headers, freeze it.
- Return the sheet object.

Called from `logToSheet_` and `summarizeContext_` — both lazily ensure structure.

### 3b. `extractHealthData_(userText)` — JSON-mode Gemini
**Purpose:** Pull a partial health record from free Thai text. Returns a sanitized object; missing fields are simply omitted.

```js
function extractHealthData_(userText) // returns object
```
Logic:
- Call Gemini with a tight Thai extraction prompt asking ONLY for the 6 numeric/text fields.
- `generationConfig: { temperature: 0, responseMimeType: 'application/json' }` → guaranteed JSON.
- Parse → for each numeric field, if outside `SANITY_BOUNDS` drop that field (log dropped value).
- Return cleaned object. `{}` if nothing usable.
- All errors → return `{}`, never throw.

Prompt sketch (Thai, ~10 lines): "ดึงเฉพาะข้อมูลที่ปรากฏจริง ถ้าไม่มี ส่ง `{}`. หน่วย: kg, แก้ว, นาที, ชั่วโมง, 1–5."

### 3c. `logToSheet_(data, sourceText)` — race-safe upsert
**Purpose:** One row per day. Merge new fields into today's row if it exists; otherwise append.

```js
function logToSheet_(data, sourceText) // returns void
```
Logic:
- `const lock = LockService.getScriptLock(); lock.waitLock(5000);` then `try/finally { lock.releaseLock(); }`
- `sheet = setupSheet_()`
- Today = `Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd')`
- Read column A → find today's row index, or `null`.
- **Merge rule:** for each field in `data`, new value replaces existing (latest report wins — including `water_glasses`, since Bright reports running totals, not deltas).
- Always update `updated_at` and append/replace `source_message` (truncated to `SOURCE_MSG_MAX_LEN`).
- `setValues([[...]])` for update, `appendRow([...])` for insert.
- On any exception → `Logger.log` and swallow. Never throw.

### 3d. `summarizeContext_()` — reads Sheet, writes property
**Purpose:** Generate the short Thai behavioral summary that becomes `USER_CONTEXT`.

```js
function summarizeContext_() // returns string and writes USER_CONTEXT
```
Logic:
- `sheet = setupSheet_()`; pull rows where `date` is within `CONTEXT_WINDOW_DAYS` of today (Asia/Bangkok).
- If 0 rows → write empty string to `USER_CONTEXT`, return `''`.
- Otherwise build a compact tabular text dump (one line per day) and send to Gemini with this prompt:
  > "สรุปพฤติกรรม 7 วันล่าสุดของผู้ใช้เป็นภาษาไทย 3–4 บรรทัด เน้น: น้ำ ออกกำลังกาย น้ำหนัก แนวโน้ม. ห้ามวินิจฉัยโรค ห้ามแนะนำยา."
- `temperature: 0.3, maxOutputTokens: 250`.
- Save result to `USER_CONTEXT`, return it.

### 3e. `dailyContextUpdate()` — cron entry point
```js
function dailyContextUpdate() {
  try { summarizeContext_(); }
  catch (err) { Logger.log('dailyContextUpdate error: ' + err.message); }
}
```
Triggered nightly at 23:00 Asia/Bangkok (see `setupTriggers` update in 4c).

### 3f. `runSelfTest_()` — one-click verification
**Purpose:** Single function to validate the whole pipeline end-to-end without sending a LINE message.

```js
function runSelfTest_() // returns void
```
Logic:
- `setupSheet_()` → asserts headers exist.
- `extractHealthData_('วันนี้ดื่มน้ำ 6 แก้ว เดิน 30 นาที น้ำหนัก 74.5')` → asserts 3 fields present.
- `extractHealthData_('น้ำหนัก 750')` → asserts `weight_kg` dropped by sanity bound.
- `logToSheet_({weight_kg: 74.5, water_glasses: 6}, 'self-test #1')` → row exists for today.
- `logToSheet_({sleep_hr: 7}, 'self-test #2')` → same row, merged (not duplicated).
- `summarizeContext_()` → asserts non-empty string written to `USER_CONTEXT`.
- `Logger.log` each step's pass/fail. Throws on first failure.

Run this once after every deploy. Replaces manual multi-step testing.

---

## Step 4 — Modify existing functions

### 4a. `handleMessage_` — tail-append Phase A
At the very end of the function (after `logToDoc_('OUT', replyText);`):
```js
// Phase A: structured capture (best-effort, never blocks reply)
try {
  const data = extractHealthData_(userText);
  if (Object.keys(data).length > 0) {
    logToSheet_(data, userText);
  }
} catch (err) {
  Logger.log('capture pipeline error: ' + err.message);
}
```

### 4b. `callGemini_` — prepend `USER_CONTEXT` for Phase B
No signature change. Read property inside the function:
```js
function callGemini_(userText, history) {
  // ...existing apiKey/url/contents setup...
  const userContext = PropertiesService.getScriptProperties().getProperty('USER_CONTEXT') || '';
  const systemText = userContext
    ? SYSTEM_PROMPT + '\n\nบริบทพฤติกรรม 7 วันล่าสุดของผู้ใช้:\n' + userContext
    : SYSTEM_PROMPT;

  const requestBody = {
    systemInstruction: { parts: [{ text: systemText }] },
    contents: contents,
    generationConfig: { temperature: 0.7, maxOutputTokens: 400, topP: 0.9 }
  };
  // ...rest unchanged...
}
```
Until Phase B ships, `USER_CONTEXT` is empty and this branch is a no-op — safe to deploy alongside Phase A.

### 4c. `setupTriggers()` — add nightly summarizer
Extend the existing cleanup-then-create pattern:
- Delete any existing `morningCheckin` AND `dailyContextUpdate` triggers.
- Create `morningCheckin` at 07:00 Asia/Bangkok (unchanged).
- Create `dailyContextUpdate` at 23:00 Asia/Bangkok daily.

---

## Step 5 — Staged rollout

### Day 0 — Ship Phase A
1. `clasp push` (code + manifest).
2. Editor → run `setupSheet_` → accept Sheets scope → confirm headers appear in row 1 of the Sheet.
3. Editor → run `runSelfTest_` → all green.
4. Send a real Thai LINE message reporting water + exercise → confirm row in Sheet, bot replies normally.
5. Watch for 3–5 days. Spot-check Sheet vs. messages. Tune `SANITY_BOUNDS` or extraction prompt if needed.

### Day ~5 — Ship Phase B
1. Editor → run `summarizeContext_` once manually → inspect `USER_CONTEXT` value.
2. Editor → run `setupTriggers` → confirm two triggers now exist.
3. Next morning's 07:00 check-in still works; next evening's 23:00 cron updates context; next reply reflects Bright's actual week.

### Kill switch (if Phase B output is bad)
- Delete the `dailyContextUpdate` trigger.
- Delete the `USER_CONTEXT` property.
- Bot falls back to pure Phase A behavior with zero code change.

---

## Sheet schema (tab name: `daily_log`)

| col | type | merge rule | notes |
|---|---|---|---|
| `date` | `yyyy-MM-dd` (Asia/Bangkok) | key | one row per day |
| `weight_kg` | number | replace-latest | sanity 40–200 |
| `water_glasses` | number | replace-latest | running total, not delta |
| `exercise_min` | number | replace-latest | running total per day |
| `sleep_hr` | number | replace-latest | last night's sleep |
| `mood_1to5` | number | replace-latest | 1–5 |
| `note` | string | replace-latest | free text |
| `source_message` | string | replace-latest | truncated to 200 chars, debug trail |
| `updated_at` | ISO timestamp | always overwritten | debugging |

---

## Verification — Phase A

1. `runSelfTest_()` returns clean → core pipeline works.
2. Send Thai message with 3 numbers → Sheet row populated; bot replies normally.
3. Send second message same day with different field → same row merged, others preserved.
4. Send message with absurd number ("น้ำหนัก 750") → other fields land, bad field dropped, log warning present.
5. Temporarily set `SHEET_ID` to garbage → bot still replies, error logged, no crash.
6. Two messages within a second (simulate by running `logToSheet_` twice in parallel via two editor tabs) → both land, no overwrite, single row for today.

## Verification — Phase B

1. After 23:00 cron fires → `USER_CONTEXT` property contains 3–4 Thai lines about the last 7 days.
2. Send a LINE message → bot's reply references actual recent behavior (e.g. "เห็นว่าเมื่อวานออกกำลังกายแล้ว เก่งมาก…").
3. Clear `USER_CONTEXT` → reply tone returns to generic. Restore → personalized again.

---

## Out of scope (explicit deferrals)
- Streak detection / week-over-week deltas — derivable later from the Sheet without code changes.
- Doctor appointment reminders, emergency escalation, Rich Menu — already on the roadmap.
- Migrating Google Doc logs into the Sheet — Doc stays as raw audit trail.
- Multi-user support — `SHEET_ID` is single-tenant by design.
