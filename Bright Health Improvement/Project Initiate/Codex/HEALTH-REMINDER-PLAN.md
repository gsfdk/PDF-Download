# Health Reminder Spec — Phase A.2

> Implemented alongside the Phase A.1 soak. Phase B recall remains dormant.
> Code lives one level up in `../HealthCoachBot.gs`.

## Goal

Add reusable health reminders for blood-test rechecks, doctor appointments, and
follow-ups. Keep future events separate from daily metrics, auditable in Google
Sheets, and proactive through LINE without providing medical interpretation.

## LINE interface

- Natural Thai requests are supported, for example: `อีก 3 เดือนจะไปตรวจเลือด`.
- Relative dates create a pending request and ask for an exact date.
- Exact dates accept ISO (`2026-08-31`), Thai Gregorian
  (`31 สิงหาคม 2026`), and Thai Buddhist (`31 สิงหาคม 2569`) formats.
- Commands:
  - `ดูรายการเตือน`
  - `ยกเลิกการเตือน HR-0001`
  - `ทำรายการ HR-0001 เสร็จแล้ว`

Pending requests live in Script Property `PENDING_HEALTH_REMINDER` for up to 24
hours. Management replies bypass normal coaching history but remain in the
Google Doc raw conversation log.

## Storage

Google Sheet tab: `health_reminders`

| Column | Purpose |
|---|---|
| `id` | Stable ID such as `HR-0001` |
| `category` | `blood_test`, `doctor_appointment`, or `follow_up` |
| `title` | Short Thai description |
| `due_date` | Normalized `yyyy-MM-dd` |
| `status` | `active`, `completed`, or `cancelled` |
| `source_message` | Original LINE request |
| `created_at`, `updated_at` | Audit timestamps |
| `sent_7d_at`, `sent_1d_at`, `sent_due_at` | Notification dedup |
| `overdue_followup_sent_at` | One-time evening follow-up dedup |
| `completed_at`, `cancelled_at` | Lifecycle audit |

## Schedule

- `healthReminderScan()` runs daily around 09:00 Asia/Bangkok.
- Active reminders push LINE messages 7 days before, 1 day before, and on the
  due date. A stage is recorded only after LINE returns a successful HTTP code.
- A due item that remains open is mentioned once in the next evening check-in.
  The bot does not send daily standalone chasers.
- Phase B `dailyContextUpdate` stays disabled.

## Verification

1. Run public `runHealthReminderSelfTest()` and require all assertions to pass.
2. Run `setupTriggers()` and confirm four Phase A.2 triggers: morning check-in,
   evening check-in, unanswered evening reminder, and health reminder scan.
3. Send `อีก 3 เดือนจะไปตรวจเลือด`, provide an exact date, then run
   `ดูรายการเตือน`.
4. Confirm the `health_reminders` row and Google Doc raw log.
5. Cancel the test reminder with `ยกเลิกการเตือน HR-xxxx`.

## Explicit deferrals

- Google Calendar synchronization
- Medication reminders
- Generic personal reminders
- Recurring reminder rules
- Lab-result interpretation
- Multi-user support

