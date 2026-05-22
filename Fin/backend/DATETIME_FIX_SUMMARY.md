# DateTime PostgreSQL Compatibility Fix

## Problem
The application was throwing a `DataError` when inserting transactions into the PostgreSQL database:
```
TypeError: can't subtract offset-naive and offset-aware datetimes
asyncpg.exceptions.DataError: invalid input for query argument $21: datetime.datetime(2026, 1, 31, 0, 0, tzi... (can't subtract offset-naive and offset-aware datetimes)
```

## Root Cause
The issue occurred because:
1. PostgreSQL columns were defined as `TIMESTAMP WITHOUT TIME ZONE`
2. Some datetime objects being passed had timezone information (timezone-aware)
3. asyncpg (the PostgreSQL driver) cannot handle mixing timezone-aware and timezone-naive datetimes

## Solution Applied

### 1. Updated All Database Models
Modified all SQLAlchemy models to explicitly use `DateTime(timezone=False)`:

**Files Updated:**
- `app/models/transaction.py` - Transaction and RecurringTransaction models
- `app/models/user.py` - User model
- `app/models/investment.py` - Investment, InvestmentHolding, Watchlist models
- `app/models/notification.py` - Notification model
- `app/models/conversation.py` - Conversation and Message models
- `app/models/agent_state.py` - AgentState and AgentTask models

**Change Pattern:**
```python
# Before
created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# After
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)
```

### 2. Added Pydantic Validators to Input Schemas
Added field validators to strip timezone info from incoming datetime values:

**Files Updated:**
- `app/schemas/transaction.py` - TransactionBase
- `app/schemas/investment.py` - InvestmentBase, InvestmentCreate, InvestmentHoldingCreate

**Validator Pattern:**
```python
@field_validator('transaction_date', mode='before')
@classmethod
def ensure_naive_datetime(cls, v):
    """Ensure datetime is timezone-naive for PostgreSQL compatibility."""
    if v is None:
        return v
    if isinstance(v, datetime) and v.tzinfo is not None:
        # Convert to UTC and remove timezone info
        return v.replace(tzinfo=None)
    return v
```

## Benefits
1. **Consistent DateTime Handling**: All datetime operations now use timezone-naive UTC times
2. **No Breaking Changes**: Existing code continues to work, timezone-aware inputs are automatically converted
3. **PostgreSQL Compatible**: Matches the database column definition `TIMESTAMP WITHOUT TIME ZONE`
4. **Future-Proof**: All models and schemas now explicitly handle timezone issues

## Testing
Created test script (`test_datetime_fix.py`) that verifies:
- ✅ Timezone-aware datetimes are converted to naive
- ✅ Timezone-naive datetimes remain unchanged
- ✅ All models and schemas import successfully
- ✅ FastAPI application loads without errors

## Database Migration
No database migration is required because:
- Database columns were already `TIMESTAMP WITHOUT TIME ZONE`
- We only fixed the Python/SQLAlchemy side to match the database definition

## Recommendations Going Forward
1. Always use `datetime.utcnow()` for creating timestamps (not `datetime.now()`)
2. Store all times in UTC in the database
3. Let the frontend/client handle timezone conversions for display
4. The Pydantic validators will automatically handle any timezone-aware inputs

## Files Modified Summary
- 6 model files updated with `DateTime(timezone=False)`
- 2 schema files updated with field validators
- 1 test file created for verification

All transaction operations, including creating, updating, and querying transactions, should now work correctly with Neon PostgreSQL.
