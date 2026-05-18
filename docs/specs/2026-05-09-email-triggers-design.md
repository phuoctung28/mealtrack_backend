# Email Triggers System Design

**Date:** 2026-05-09  
**Status:** Approved  
**App:** Nutree

## Problem Statement

Need lifecycle email triggers for:
1. Welcome email when user completes onboarding
2. Re-engagement email when trial users are inactive (3+ days)
3. Trial expiring reminder (2 days before expiration)
4. Cancellation email when trial is cancelled via RevenueCat

## Solution Overview

Event-driven email system using Resend (free tier: 100/day, 3000/month) with psychology-informed templates.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Triggers                                 │
├──────────────────┬──────────────────┬───────────────────────────┤
│ UserOnboardedEvent│ Scheduled Job    │ RevenueCat Webhook        │
│ (welcome email)   │ (re-engagement)  │ (cancellation email)      │
└────────┬─────────┴────────┬─────────┴─────────────┬─────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EmailEventHandlers                            │
│  - WelcomeEmailHandler                                          │
│  - ReengagementEmailHandler                                     │
│  - TrialCancellationEmailHandler                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      EmailService                                │
│  - send_welcome_email(user)                                     │
│  - send_reengagement_email(user, days_inactive)                 │
│  - send_trial_expiring_email(user, days_left)                   │
│  - send_cancellation_email(user)                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ResendEmailAdapter                             │
│  - send(to, subject, html_body)                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model Changes

### User Table Additions

```python
welcome_email_sent_at = Column(DateTime(timezone=True), nullable=True)
email_opt_out = Column(Boolean, default=False, nullable=False)
```

### New Table: email_logs

```python
class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    email_type = Column(String(50), nullable=False)  # welcome, reengagement_day3, trial_expiring, cancelled
    sent_at = Column(DateTime(timezone=True), nullable=False)
    resend_message_id = Column(String(255), nullable=True)
    status = Column(String(20), default="sent")  # sent, failed, bounced
```

### Index for Scheduled Job

```sql
CREATE INDEX idx_users_last_accessed_active 
ON users(last_accessed) 
WHERE is_active = true AND email_opt_out = false;
```

## Components

### 1. EmailServicePort (Interface)

**File:** `src/domain/ports/email_service_port.py`

```python
class EmailServicePort(ABC):
    @abstractmethod
    async def send_email(
        self, 
        to: str, 
        subject: str, 
        html_body: str,
        tags: list[str] | None = None
    ) -> EmailResult:
        pass
```

### 2. ResendEmailAdapter

**File:** `src/infra/adapters/resend_email_adapter.py`

- Wraps Resend SDK
- Handles rate limiting (10 req/sec on free tier)
- Returns `EmailResult` with message_id or error

### 3. EmailService

**File:** `src/domain/services/email_service.py`

Methods:
- `send_welcome_email(user)` - Personalized welcome with TDEE
- `send_reengagement_email(user, days_inactive)` - Loss-framed reminder
- `send_trial_expiring_email(user, days_left)` - Urgency with real data
- `send_cancellation_email(user)` - Feedback request + pause option

### 4. EmailTemplateRenderer

**File:** `src/infra/services/email_template_renderer.py`

- Jinja2-based HTML rendering
- Loads templates from `src/infra/templates/emails/`

### 5. Email Templates

**Directory:** `src/infra/templates/emails/`

| Template | Subject | Psychology |
|----------|---------|------------|
| `welcome.html` | "Your nutrition journey starts now, {{first_name}}" | Personalization, peak motivation, single CTA |
| `reengagement.html` | "We saved your progress, {{first_name}}" | Loss aversion, streak preservation |
| `trial_expiring.html` | "In 2 days, your macros go dark" | Specific loss framing, real user data |
| `trial_cancelled.html` | "Before you go — one quick question?" | Exit intent, pause option, door open |

All templates include:
- Mobile-first design
- Unsubscribe footer
- One primary CTA only

### 6. WelcomeEmailHandler

**File:** `src/app/handlers/event_handlers/welcome_email_handler.py`

- Listens to `UserOnboardedEvent`
- Checks `welcome_email_sent_at` to prevent duplicates
- Checks `email_opt_out` preference
- Logs to `email_logs` table

### 7. ScheduledEmailService

**File:** `src/infra/services/scheduled_email_service.py`

Runs daily (integrated with existing scheduler pattern):
- Find inactive trial users (3+ days since `last_accessed`)
- Find trials expiring in 2 days
- Check `email_logs` to prevent duplicate sends within 7 days
- Send appropriate emails

### 8. RevenueCat Webhook Integration

**Modify:** Existing RevenueCat webhook handler

When subscription status changes to `cancelled`:
- Call `email_service.send_cancellation_email(user)`

## Email Content (Psychology-Informed)

### Welcome Email
- **Timing:** Within 5 minutes of onboarding
- **Content:** Show their TDEE, single CTA "Log your first meal"
- **Social proof:** "Join 10K+ users tracking daily"

### Re-engagement (Day 3)
- **Subject:** "We saved your progress, {{first_name}}"
- **Content:** Show streak they'll lose, "Pick up where you left off"
- **Optional:** One question "What got in the way?"

### Trial Expiring (2 days)
- **Subject:** "In 2 days, your macros go dark"
- **Content:** Show actual data (meals logged, streaks), upgrade CTA
- **Framing:** Loss-based, not gain-based

### Cancellation
- **Subject:** "Before you go — one quick question?"
- **Content:** Single-choice reason, pause option (30-day break)
- **Tone:** Respectful, door open to return

## Error Handling

| Error | Action |
|-------|--------|
| Rate limit (429) | Retry after 1 second delay |
| Invalid email | Log as failed, don't retry |
| Network error | Log, retry up to 3 times |
| Resend API error | Log with details, alert if persistent |

## Duplicate Prevention

| Email Type | Prevention |
|------------|------------|
| Welcome | Check `user.welcome_email_sent_at` |
| Re-engagement | Check `email_logs` for same type within 7 days |
| Trial expiring | Check `email_logs` for same type this trial period |
| Cancellation | Check `email_logs` for cancellation this subscription |

## Configuration

```python
# .env
RESEND_API_KEY=re_xxxx
EMAIL_FROM=Nutree <hello@nutree.app>
EMAIL_ENABLED=true  # false in dev/test
```

## Testing Strategy

| Test Type | Scope |
|-----------|-------|
| Unit | EmailService with mocked adapter |
| Unit | Template rendering with test data |
| Unit | Duplicate prevention logic |
| Integration | Resend sandbox mode |
| E2E | Manual test on staging |

## Files to Create

| File | Description |
|------|-------------|
| `src/domain/ports/email_service_port.py` | Port interface |
| `src/infra/adapters/resend_email_adapter.py` | Resend SDK wrapper |
| `src/domain/services/email_service.py` | Email business logic |
| `src/infra/services/email_template_renderer.py` | Jinja2 renderer |
| `src/infra/templates/emails/base.html` | Shared layout |
| `src/infra/templates/emails/welcome.html` | Welcome template |
| `src/infra/templates/emails/reengagement.html` | Re-engagement template |
| `src/infra/templates/emails/trial_expiring.html` | Trial expiring template |
| `src/infra/templates/emails/trial_cancelled.html` | Cancellation template |
| `src/app/handlers/event_handlers/welcome_email_handler.py` | Welcome event handler |
| `src/infra/services/scheduled_email_service.py` | Scheduled job |
| `src/infra/database/models/email_log.py` | Email log model |
| `alembic/versions/xxx_add_email_fields.py` | Migration |

## Files to Modify

| File | Change |
|------|--------|
| `src/infra/database/models/user/user.py` | Add `welcome_email_sent_at`, `email_opt_out` |
| `src/infra/config/settings.py` | Add Resend config |
| `requirements.txt` | Add `resend` package |
| RevenueCat webhook handler | Add cancellation email trigger |
| `src/api/main.py` | Register scheduled email service |

## Trial User Definition

A "trial user" is identified by:
- Has an active subscription (`subscriptions.status = 'active'`)
- Subscription `product_id` contains "trial" OR
- Subscription `purchased_at` is within trial period (typically 7 days) AND not yet converted

Query:
```sql
SELECT u.* FROM users u
JOIN subscriptions s ON u.id = s.user_id
WHERE s.status = 'active'
  AND s.purchased_at > NOW() - INTERVAL '7 days'
  AND s.product_id LIKE '%trial%'
```

Alternatively, check RevenueCat `entitlements` via API for precise trial status.

## Success Criteria

- Welcome email sent within 5 minutes of onboarding
- Re-engagement email sent on day 3 of inactivity (trial users only)
- Trial expiring email sent 2 days before expiration
- Cancellation email sent immediately on RevenueCat webhook
- No duplicate emails
- User can opt out via unsubscribe link
- All emails logged in `email_logs` table
