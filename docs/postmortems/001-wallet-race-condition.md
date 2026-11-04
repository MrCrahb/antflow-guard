# Postmortem 001: The Double-Spend / Lost-Update Concurrency Race Condition

- **Incident Classification:** Critical (P0 Data Integrity Vulnerability)
- **Service Affected:** `app.services.settlement.settle_cross_border_payment`
- **Root Cause Category:** Concurrency Control & Database Transaction Isolation Anomaly

---

## 1. Executive Summary
During high-throughput settlement testing simulating 15 concurrent settlement requests against the same merchant wallet, the ledger experienced a severe **Lost Update Anomaly**. Instead of the expected final balance of `975.0000 MYR`, the wallet balance stalled at `65.0000 MYR`. Fourteen balance increments were silently overwritten, and concurrent identical idempotency keys produced unhandled `IntegrityError` collisions resulting in HTTP 500 Internal Server Errors.

---

## 2. Root Cause Analysis (Technical Deep Dive)

### Bug A: Lost Update under Read Committed Isolation
In default `Read Committed` isolation:
```sql
-- Coroutine A and Coroutine B run concurrently:
Coroutine A: SELECT balance FROM wallets WHERE merchant_id = 'merch_01'; -- reads 0.0000
Coroutine B: SELECT balance FROM wallets WHERE merchant_id = 'merch_01'; -- reads 0.0000
Coroutine A: UPDATE wallets SET balance = 65.0000 WHERE id = '...';      -- writes 65.0000
Coroutine B: UPDATE wallets SET balance = 65.0000 WHERE id = '...';      -- overwrites with 65.0000!
```
Because neither coroutine acquired an exclusive row lock prior to reading the mutable balance state, Coroutine B read stale data and overwrote Coroutine A's committed write.

### Bug B: In-Flight Duplicate Idempotency Race Condition
When two identical requests arrived simultaneously:
1. Request 1 checked `select(Transaction).where(idempotency_key == key)` -> returned None.
2. Request 2 checked `select(Transaction).where(idempotency_key == key)` -> returned None.
3. Both proceeded to insert. Request 1 flushed and committed. Request 2 failed on `session.flush()` with `sqlalchemy.exc.IntegrityError` (violating `UNIQUE` constraint).
4. Without proper retry and transactional isolation, Request 2 attempted to read the newly committed record before Request 1 finalized its transaction, crashing with HTTP 500 (`No row was found`).

---

## 3. Engineering Resolution

### Mitigation 1: Pessimistic Row Locking (`SELECT ... FOR UPDATE`)
All queries reading a merchant's `Wallet` for balance modification must lock the specific row:
```python
wallet_lock_stmt = (
    select(Wallet)
    .where(
        Wallet.merchant_id == payload.merchant_id,
        Wallet.currency == payload.settled_currency,
    )
    .with_for_update()  # Serializes concurrent updates at the database row level
)
```

### Mitigation 2: Graceful Idempotency Collision Fallback
Wrapped duplicate key collisions in an `IntegrityError` handler with progressive jitter retry, ensuring the in-flight transaction completes before safely replaying the committed transaction:
```python
except IntegrityError:
    for attempt in range(5):
        await asyncio.sleep(0.05 * (attempt + 1))
        async with session.begin():
            existing_tx = (await session.execute(...)).scalar_one_or_none()
            if existing_tx:
                return PaymentSettlementResponse(..., idempotent_replay=True)
```

---

## 4. Verification & Validation
- **Concurrency Test:** `tests/integration/test_concurrency.py`
  - 10 identical simultaneous requests -> All 10 returned HTTP 200 OK (1 primary, 9 idempotent replays).
  - 15 concurrent distinct settlements -> Final balance exactly `975.0000 MYR` (zero lost updates).
- **Test Suite Status:** PASSED (7/7 tests).
