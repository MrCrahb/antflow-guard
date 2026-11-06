# AI Engineering & Review Log

This log documents human-in-the-loop engineering reviews, edge cases discovered, and governance interventions when pairing with AI agents throughout the development of **AntFlow Guard**.

---

## Log Entries

### Entry 001 — Environment Architecture & Anti-Autopilot Initialization
- **Date:** 2026-11-04
- **Context:** Project kickoff and environment setup.
- **Decision:** System Python on macOS was 3.9.6, lacking modern type-hinting ergonomics and below the target Python 3.12 specified for the microservice. Instead of polluting host global libraries or requiring Homebrew, configured standalone `uv` to manage isolated CPython 3.12.16 in `.venv`.
- **Database Architecture:** Decided on Cloud Serverless PostgreSQL (Neon / Supabase) to guarantee genuine row-level lock semantics (`SELECT ... FOR UPDATE`) over SQLite's coarse file-level locking, enabling true multi-client concurrency tests.
- **Verification Question:** *Why is SQLite unsuitable for testing production FinTech concurrency bugs involving `with_for_update()`?*
  - *Answer:* SQLite acquires a database-wide write lock rather than granular row locks on individual records (`Wallet`), which masks row-level race conditions and prevents replicating real-world Postgres transaction isolation behavior.

### Entry 002 — Observability Architecture, RED Metrics & SRE Dashboards
- **Date:** 2026-11-06
- **Context:** Implementing mission-critical operational telemetry for cross-border settlements.
- **Architectural Guardrails & Decisions:**
  1. *Cardinality Protection:* Raw endpoint URLs with path parameters (e.g. `/api/v1/merchants/{merchant_id}/wallets`) would cause metric cardinality explosion if measured naively. Implemented route matching template resolution in `PrometheusMiddleware` to normalize paths.
  2. *Zero-Touch Business Isolation:* Preserved core financial ledger algorithms and risk heuristic triage in `settlement.py` and `fx_service.py` completely untouched; business metrics are recorded at the API boundary.
  3. *Zero-Click Grafana Provisioning:* Provisioned Prometheus datasources and the SRE dashboard declaratively via YAML/JSON so engineers and operators have zero manual configuration on fresh deployments.
  4. *Multi-Tier SRE Triad:* Configured RED infrastructure metrics (Rate, Errors, Duration) alongside business invariant counters (`SETTLED` vs `FLAGGED_HIGH_RISK`) and automated Prometheus alert rules.
- **Verification Question:** *Why measure p95/p99 tail latency via Prometheus histograms rather than simple averages in financial payment settlement?*
  - *Answer:* Arithmetic mean latency hides severe tail bottlenecks caused by lock contention (`SELECT ... FOR UPDATE`), network FX latency, or database serialization during transaction bursts. Histograms bucket request durations deterministically, enabling accurate quantile evaluation (`histogram_quantile`) across dynamic traffic windows.

---
