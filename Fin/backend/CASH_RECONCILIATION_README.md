# Cash Reconciliation & Smart Nudging Feature

## Overview
AI-powered cash tracking that proactively nudges users to reconcile untracked cash withdrawals with intelligent expense suggestions.

## Features Implemented

### 1. Backend Services

#### **Cash Reconciliation Service** (`app/services/cash_reconciliation_service.py`)
- Calculates untracked cash: `Total ATM Withdrawals - Tracked Cash Expenses`
- Generates probabilistic expense suggestions based on:
  - Historical cash spending patterns
  - Day-of-week routines
  - Common spending categories
- Configurable lookback window (default: 30 days)

#### **Notification System** (`app/models/notification.py`)
- Persistent notification storage in PostgreSQL
- User-specific notifications with read/unread tracking
- Payload support for rich notification data (suggestions, amounts, etc.)

#### **API Endpoints** (`app/api/v1/endpoints/cash_check.py`)
- `GET /api/v1/cash-check/summary` - Get cash position + AI suggestions
- `POST /api/v1/cash-check/quick-add` - Quick-add cash expense
- `POST /api/v1/cash-check/still-have-cash` - Skip nudge (user confirms cash in wallet)
- `GET /api/v1/cash-check/notifications` - Fetch cash-check notifications
- `POST /api/v1/cash-check/notifications/{id}/mark-read` - Mark notification read

### 2. Celery Background Task

#### **Nightly Cash Check** (`app/services/tasks.py`)
- Scheduled at **11 PM IST** (23:00 Asia/Kolkata)
- Runs for all active users
- Creates notifications when:
  - Untracked cash ≥ ₹1,000
  - 3+ days since last withdrawal
- Includes personalized suggestions in notification payload

#### **Celery Beat Configuration** (`app/services/celery_beat_config.py`)
```python
'nightly-cash-check': {
    'task': 'nightly_cash_check',
    'schedule': crontab(hour=17, minute=30),  # 11 PM IST
}
```

### 3. Frontend Components

#### **Add Transaction Modal** (`components/common/AddTransactionModal.tsx`)
- Beautiful modal for manual transaction entry
- Supports:
  - Amount, category, subcategory
  - Description, date
  - Auto-tags as "cash" for reconciliation
- Integrated into "Add New" button on Transactions page

#### **Untracked Cash Widget** (`components/common/UntrackedCashWidget.tsx`)
- Shows estimated untracked cash amount
- Expandable quick-add suggestions
- One-tap expense logging
- Progress bar visualization
- Displays on:
  - Dashboard (main overview)
  - Transactions page

## How It Works

### Cash Withdrawal Detection
Transactions are identified as cash withdrawals if:
1. Tagged with `cash_withdrawal` (primary signal)
2. Description/merchant contains keywords: "atm", "cash withdrawal", "withdraw"

### Cash Spend Detection
Transactions are identified as cash spends if:
1. Tagged with `cash` or `cash_spend`
2. Description contains "cash" (for manual entries)

### Suggestion Algorithm
1. Analyzes last 90 days of cash spending
2. Groups by subcategory (groceries, transport, food, etc.)
3. Weights same-weekday expenses higher (routine detection)
4. Computes P25/P50/P75 amounts for robust ranges
5. Returns top 4 suggestions sorted by probability

### Example Notification Payload
```json
{
  "type": "cash_check",
  "title": "💰 Cash Check-In",
  "message": "You have ₹5,200 in untracked cash. Tracked so far: ₹2,000. Quick add expenses?",
  "payload": {
    "cash_position": {
      "estimated_untracked_cash": 5200,
      "total_withdrawn": 10000,
      "tracked_cash_spend": 2000,
      "days_since_withdrawal": 5
    },
    "suggestions": [
      {
        "label": "Groceries",
        "subcategory": "groceries",
        "typical_amount": 500,
        "amount_range": [300, 700],
        "probability": 0.34
      },
      ...
    ]
  }
}
```

## Running the System

### 1. Start Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Start Celery Worker
```bash
celery -A app.services.celery_app worker --loglevel=info
```

### 3. Start Celery Beat (Scheduler)
```bash
celery -A app.services.celery_beat_config beat --loglevel=info
```

### 4. Start Frontend
```bash
cd frontend
npm run dev
```

## Database Migration

The `Notification` table will be auto-created via `init_db()` in development. For production:

```bash
# Using Alembic (if set up)
alembic revision --autogenerate -m "Add notification table"
alembic upgrade head
```

## Configuration

### Environment Variables
No new environment variables required. Uses existing:
- `DATABASE_URL` - PostgreSQL connection
- `CELERY_BROKER_URL` - Redis for Celery
- `CELERY_RESULT_BACKEND` - Redis for results

### Adjusting Schedule
Edit `app/services/celery_beat_config.py`:
```python
'nightly-cash-check': {
    'task': 'nightly_cash_check',
    'schedule': crontab(hour=17, minute=30),  # Change hour/minute
}
```

### Thresholds
Adjust in `app/services/tasks.py`:
```python
if position["eligible_for_nudge"] and position["estimated_untracked_cash"] >= 1000:
    # Change 1000 to your desired threshold
```

## User Experience Flow

1. **User withdraws ₹10,000 from ATM** (tracked via SMS/bank sync)
2. **User manually logs ₹2,000 cash expenses** over 3 days
3. **At 11 PM IST**, system runs nightly check:
   - Detects ₹8,000 untracked cash
   - Generates suggestions: "Groceries ₹500", "Transport ₹200", etc.
   - Creates notification
4. **User opens app**, sees:
   - Dashboard widget: "Untracked Cash: ₹8,000"
   - Click "Quick Add" → suggestions appear
   - Tap "Groceries ₹500" → instant logging
5. **Notification marked read**, widget updates to ₹7,500 remaining

## Future Enhancements

- **ML-powered suggestions** (train on user history + demographics)
- **Location-based hints** (if GPS permission granted)
- **Push notifications** (via FCM/APNs for mobile app)
- **Voice logging** ("Hey Finbuddy, I spent ₹500 on groceries")
- **Receipt OCR** integration from existing OCR agent

## Testing

### Manual Test
1. Create test user
2. Add ATM withdrawal transaction (tag: `cash_withdrawal`, amount: 10000)
3. Add cash expense (tag: `cash`, amount: 2000)
4. Call API: `GET /api/v1/cash-check/summary`
5. Should return ~₹8,000 untracked + suggestions

### Run Nightly Task Manually
```python
from app.services.tasks import nightly_cash_check
result = nightly_cash_check()
print(result)  # Should show notifications created
```

## Support

For questions or issues:
- Check logs: `celery worker` and `uvicorn` output
- Review Celery Beat logs for scheduler issues
- Verify Redis is running: `redis-cli ping` (should return PONG)
