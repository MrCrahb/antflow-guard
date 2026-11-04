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

---
