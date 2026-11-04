# AntFlow Guard — Cross-Border Payment Routing, FX Settlement & Real-Time Anomaly Engine

> A production-grade distributed microservice and operator console for high-reliability cross-border merchant settlements, multi-currency wallet ledger management, and real-time FX anomaly triage.

[![CI/CD Pipeline](https://github.com/your-username/antflow-guard/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-username/antflow-guard/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Hypothesis](https://img.shields.io/badge/Hypothesis-Property--Tested-green.svg)](https://hypothesis.readthedocs.io/)
[![Bandit SAST](https://img.shields.io/badge/Security-Bandit%20SAST-critical.svg)](https://bandit.readthedocs.io/)

---

## 1. Project Overview & Architectural Pitch

**AntFlow Guard** is a mission-critical cross-border merchant settlement API and real-time operator console designed for global digital commerce, multi-currency treasury operations, and regional e-wallet interoperability.

The engine handles multi-currency transactions across Southeast Asia and global corridors (CNY $\rightarrow$ MYR, USD $\rightarrow$ MYR, SGD $\rightarrow$ MYR), enforcing:
- **Zero Double-Charging Guarantees:** Strict deduplication via `X-Idempotency-Key` and resilient recovery against in-flight race conditions.
- **Pessimistic Row-Level Concurrency Control:** `SELECT ... FOR UPDATE` serialization preventing negative balances and lost updates during parallel settlements.
- **Sub-Cent Financial Precision:** 100% `decimal.Decimal` computation paired with Banker's Rounding (`ROUND_HALF_EVEN`) to eliminate statistical drift.
- **Automated AI Risk Triage:** Real-time statistical heuristic analysis flagging sudden merchant volume spikes ($> 50,000$ settled units) and FX corridor deviations.
- **Continuous Ledger Reconciliation:** Immediate mathematical proof that merchant wallet balances reconcile with $0.0000$ discrepancy against immutable ledger entries.

---

## 2. System Architecture & State Machine

```
[Client / Operator Console (Next.js)]
                │
                │ POST /api/v1/payments/settle
                │ Header: X-Idempotency-Key
                ▼
      ┌────────────────────┐
      │  FastAPI Gateway   │
      └─────────┬──────────┘
                │
                ▼
     [Pre-Check Idempotency] ─── (Key Found) ───► Return Cached Response (HTTP 200, idempotent_replay=true)
                │ (New Key)
                ▼
    [Lock Merchant Wallet] (SELECT ... FOR UPDATE)
                │
                ▼
   [Banker's Rounding FX Calc] (Decimal.quantize ROUND_HALF_EVEN)
                │
                ▼
      [Heuristic Risk Triage]
                │
      ┌─────────┴─────────┐
      │                   │
  (Score >= 60)       (Score < 60)
      │                   │
      ▼                   ▼
Status: FLAGGED      Status: SETTLED
(Hold Balance)      (Increment Balance)
      │                   │
      └─────────┬─────────┘
                │
                ▼
    [Atomic Ledger Commit]
                │
                ▼
    [Live Operator Console]
```

---

## 3. Tech Stack

- **Backend API:** Python 3.12, FastAPI, Pydantic v2 (Strict Mode), SQLAlchemy 2.0 (Async).
- **Database:** PostgreSQL 16 (or Serverless Neon / Supabase) via `asyncpg`, with local async SQLite test driver.
- **Operator Console:** Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons.
- **Automated Testing:** Pytest, `pytest-asyncio`, `httpx` (async ASGI client), `hypothesis` (property-based randomized testing).
- **Security & Quality:** `bandit` (SAST scanner for FinTech vulnerabilities), `ruff` (lightning linter & formatter).
- **DevOps & CI/CD:** GitHub Actions with PostgreSQL service container, automated migrations, coverage reporting, and Gemini Flash automated failure triage.

---

## 4. Quickstart Guide

### Prerequisites
- Python 3.12 (managed via `uv` or system Python)
- Node.js $\ge 18$ & npm

### 1. Backend Service Setup
```bash
# Activate the virtual environment
source .venv/bin/activate

# (Optional) Configure database in .env
# By default, runs seamlessly on local async SQLite (antflow.db)
# Or paste your Neon Cloud Postgres URL:
# DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<dbname>?ssl=require

# Launch the FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) to view interactive OpenAPI Swagger documentation.

### 2. Frontend Operator Dashboard Setup
```bash
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to open the Live Operator Console.

### 3. Run Automated 3-Tier Test Suite
```bash
# Run 500 Hypothesis property tests + async integration + concurrency tests:
pytest -v

# Run Bandit FinTech Security Scan:
bandit -r app/ -ll

# Run Ruff Linting:
ruff check app/ tests/
```

---

## 5. Documented AI Debugging Drills & Case Studies

As part of the AI-Native SDLC mandate, two real-world FinTech vulnerabilities were simulated, isolated, debugged, and resolved:

1. [Postmortem 001: The Double-Spend & Lost-Update Concurrency Race Condition](docs/postmortems/001-wallet-race-condition.md)
   - Evaluated Read Committed anomalies under 15 parallel coroutines.
   - Resolved using pessimistic row locking (`with_for_update()`) and savepoint-level `IntegrityError` recovery.
2. [Postmortem 002: Silent Performance Degradation via N+1 Query Bottleneck](docs/postmortems/002-n-plus-1-latency.md)
   - Identified ORM lazy-loading latency explosion during merchant reconciliation.
   - Refactored to batched `selectinload` queries, achieving a $97.8\%$ latency reduction ($850\text{ms} \rightarrow 18\text{ms}$).

---

## 6. Core Architectural & Engineering Highlights

- **Core Backend & Concurrency:** *Engineered an asynchronous cross-border payment settlement API and multi-currency ledger in FastAPI and PostgreSQL, enforcing strict `NUMERIC(18, 4)` precision, `X-Idempotency-Key` deduplication, and pessimistic row-level locking (`SELECT ... FOR UPDATE`) to eliminate double-spend race conditions under concurrent load.*
- **AI-Native Engineering & SDLC:** *Designed a spec-driven, AI-native engineering workflow governed by an explicit AI constitution (`.antigravity/rules.md`) and property-based test suites, validating sub-cent financial invariants across 500 randomized parameter matrices using Hypothesis.*
- **Testing, Security & CI/CD:** *Built an enterprise multi-stage GitHub Actions CI/CD pipeline integrating Bandit SAST security scanning, ephemeral PostgreSQL service containers, and automated test suites featuring automated Gemini Flash AI failure triage on broken builds.*
