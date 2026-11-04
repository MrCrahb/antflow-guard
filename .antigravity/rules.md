# AntFlow Guard — AI Engineering & Learning Constitution

## 1. Domain Context
We are building AntFlow Guard, a high-reliability cross-border payment settlement and FX risk microservice tailored to the Ant International ecosystem (Alipay+, Antom, WorldFirst).

## 2. Non-Negotiable Financial Engineering Standards
- **NO FLOATS FOR MONEY:** Strictly use Python `decimal.Decimal` and PostgreSQL `NUMERIC(18, 4)` for monetary amounts and `NUMERIC(18, 6)` for FX rates. Never use floating-point numbers.
- **IDEMPOTENCY:** All state-mutating endpoints (`POST /api/v1/payments/settle`) MUST require an `X-Idempotency-Key` HTTP header. Duplicate requests must safely return the cached transaction response without double-crediting balances.
- **CONCURRENCY CONTROL:** Any database query reading a `Wallet` to mutate its `balance` MUST use pessimistic row-level locking (`SELECT ... FOR UPDATE` via `with_for_update()`) to eliminate race conditions and double-spending.
- **MODERN STACK:** Use SQLAlchemy 2.0 `Mapped` / `mapped_column` syntax with `AsyncSession`, Pydantic v2 (`model_validate`, `ConfigDict`), and clean async/await patterns.
- **ROUNDING:** Compute settled amounts using Banker's Rounding (`ROUND_HALF_EVEN`) to eliminate statistical drift.

## 3. Security & Observability
- Never log raw credentials or PII.
- Calculate and store execution latency and statistical Z-score / heuristic anomaly flags in `risk_audit_logs` for every transaction.

## 4. Testing Mandate
- Every service method requires both unit tests (`pytest` + `hypothesis` for boundary and property math) and async integration/concurrency tests (`asyncio.gather`).

## 5. ACTIVE LEARNING MODE (CRITICAL)
- Do NOT dump massive multi-file rewrites without explanation.
- For every architectural change (DB locking, async sessions, CI/CD config), briefly explain the underlying mechanics.
- After generating a complex module, challenge the human engineer with 1 pointed edge-case question to verify understanding.
- Document AI review discoveries and verified edge cases in `AI_ENGINEERING_LOG.md`.
