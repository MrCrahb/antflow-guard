# AntFlow Guard — Step-by-Step Observability Guide (Prometheus & Grafana)

> **Purpose:** This guide walks through adding **Prometheus metrics** and a **Grafana SRE Dashboard** to the AntFlow Guard banking microservice in simple, bite-sized steps without overcomplicating or breaking existing business logic.

---

## 1. Is This Feasible or Too Complex?

**It is 100% feasible and surprisingly lightweight.**

You do **not** need to rewrite any of your banking, wallet, or FX code. 

Adding Prometheus and Grafana only requires **3 simple building blocks**:
1. **1 Python Library (`prometheus-client`):** Adds a `/metrics` URL to your FastAPI app that outputs numbers (request count, response time).
2. **1 Config File (`prometheus.yml`):** A 10-line text file telling Prometheus: *"Every 5 seconds, read `http://api:8000/metrics`."*
3. **2 Pre-built Containers in `docker-compose.yml`:** Official, ready-made images from Docker Hub (`prom/prometheus` and `grafana/grafana`). You don't build them; they just run.

---

## 2. The 3-Step Implementation Roadmap

When you open the chat session inside the **p4 banking app** project, you can do this in 3 calm, focused phases:

### Phase 1: Expose the `/metrics` Endpoint in FastAPI
* **What you do:** Install `prometheus-client`.
* **What it adds:** A small middleware that starts a stopwatch on incoming requests and records:
  * `antflow_http_requests_total` (Rate & Status Codes: 200, 400, 500)
  * `antflow_http_request_duration_seconds` (Duration: p50, p95, p99 latency)
  * `antflow_settlement_transactions_total` (Business metric: Settled vs Flagged)
* **Verification:** Visit `http://localhost:8000/metrics` in your browser. You should see text numbers streaming live.

### Phase 2: Add Prometheus to `docker-compose.yml`
* **What you do:** Add the official Prometheus service to `docker-compose.yml` and provide a simple `prometheus.yml` scrape configuration.
* **Verification:** Open [http://localhost:9090](http://localhost:9090) in your browser. Type `antflow_http_requests_total` to see Prometheus collecting the numbers.

### Phase 3: Add Grafana & Import the SRE Dashboard
* **What you do:** Add Grafana to `docker-compose.yml` on port `3001` (to avoid conflicting with Next.js on `3000`).
* **What it adds:** A pre-configured visual dashboard with:
  * **Panel 1:** Request Latency (p50, p95, p99)
  * **Panel 2:** Traffic (Requests per second)
  * **Panel 3:** Error Rate (HTTP 2xx vs 5xx)
  * **Panel 4:** Settlement Volume & Flagged Transactions
* **Verification:** Open [http://localhost:3001](http://localhost:3001) (`admin` / `admin`) to see live graphs updating in real time.

---

## 3. Copy-Paste Prompt for your `p4 banking app` Chat

When you switch to the **p4 banking app** project in your AI chat, paste this prompt to start smoothly:

```text
Hi! I want to add Prometheus and Grafana observability to AntFlow Guard based on the OBSERVABILITY_SETUP_GUIDE.md file.

Please follow these rules:
1. Take it slow, step-by-step. Explain what you are doing before making changes.
2. Start with Phase 1 only: adding the Prometheus metrics middleware to FastAPI and exposing the /metrics endpoint.
3. Keep it simple — do not touch the core banking/FX business logic.
4. Let me verify Phase 1 works before moving to Docker Compose or Grafana.
```

---

## 4. Key Takeaways for Core Consulting Interviews

Once you finish these 3 phases, you can talk about this project with complete authority:
* *"I instrumented our cross-border payment microservice with Prometheus RED metrics (Rate, Errors, Duration) to eliminate blind spots in high-volume settlement windows."*
* *"I provisioned a Grafana operational dashboard tracking p95 and p99 transaction latencies rather than misleading averages."*
* *"I isolated business-critical invariants (zero-drift reconciliation) alongside infrastructure telemetry in a unified SRE control pane."*
