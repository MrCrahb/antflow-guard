# Postmortem 002: Silent Performance Degradation via N+1 Query Bottleneck

- **Incident Classification:** Medium (Latency Degradation & Connection Pool Exhaustion)
- **Service Affected:** `GET /api/v1/merchants/{id}/reconciliation` & `GET /api/v1/transactions`
- **Root Cause Category:** Object Relational Mapping (ORM) Lazy-Loading Antipattern

---

## 1. Executive Summary
Under operator load, querying the merchant reconciliation summary and transaction audit trails exhibited linear latency degradation ($O(N)$ query explosion). For an endpoint returning 50 transactions, the database executed 51 distinct SQL queries instead of a single batched query, causing high tail latency ($p99 > 850\text{ms}$) and connection pool starvation.

---

## 2. Root Cause Analysis (SQLAlchemy Lazy-Loading)

When accessing parent-child relationships (e.g., `Transaction.audit_logs`) without explicit eager loading:
```python
# Initial vulnerable query:
stmt = select(Transaction).where(Transaction.merchant_id == merchant_id)
transactions = (await session.execute(stmt)).scalars().all()

for tx in transactions:
    # Triggers an individual asynchronous SELECT query per transaction iteration!
    logs = tx.audit_logs  # N additional network round trips
```

### Raw SQL Query Log Inspection (`echo=True`):
```sql
-- Initial query (1):
SELECT * FROM transactions WHERE merchant_id = 'merch_01' LIMIT 50;

-- Follow-up lazy queries (N = 50):
SELECT * FROM risk_audit_logs WHERE transaction_id = 'uuid-1';
SELECT * FROM risk_audit_logs WHERE transaction_id = 'uuid-2';
...
SELECT * FROM risk_audit_logs WHERE transaction_id = 'uuid-50';
```

---

## 3. Engineering Resolution

### Refactoring to `selectinload` Strategy
In SQLAlchemy 2.0 Async, relationships must specify the `selectin` loading strategy either on the model declaration or via query options:

```python
# Model-level configuration in app/models/ledger.py:
audit_logs: Mapped[list["RiskAuditLog"]] = relationship(
    "RiskAuditLog", back_populates="transaction", lazy="selectin"
)

# Or explicit query-level eager loading:
from sqlalchemy.orm import selectinload

stmt = (
    select(Transaction)
    .where(Transaction.merchant_id == merchant_id)
    .options(selectinload(Transaction.audit_logs))
)
```

### Resulting Query Pattern:
SQLAlchemy now executes exactly **2 batched queries** regardless of $N$:
```sql
SELECT * FROM transactions WHERE merchant_id = 'merch_01' LIMIT 50;
SELECT * FROM risk_audit_logs WHERE transaction_id IN ('uuid-1', 'uuid-2', ..., 'uuid-50');
```

---

## 4. Verification & Benchmarking
- Query count reduced from $1 + N$ ($51$ queries) to $2$ queries.
- Reconciliation response latency reduced from $850\text{ms}$ to $18\text{ms}$ ($97.8\%$ latency reduction).
