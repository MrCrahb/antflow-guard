import time
from typing import Callable

from prometheus_client import (
    Counter,
    Histogram,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

# ---------------------------------------------------------------------------
# Prometheus Metric Definitions
# ---------------------------------------------------------------------------

# 1. HTTP Request Rate & Status Codes (RED: Rate & Errors)
HTTP_REQUESTS_TOTAL = Counter(
    "antflow_http_requests_total",
    "Total count of HTTP requests processed by AntFlow Guard",
    ["method", "endpoint", "status"],
)

# 2. HTTP Request Latency Duration (RED: Duration)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "antflow_http_request_duration_seconds",
    "Histogram of HTTP request durations in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0),
)

# 3. Business Metric: Settlement Transaction Volume (Settled vs Flagged)
SETTLEMENT_TRANSACTIONS_TOTAL = Counter(
    "antflow_settlement_transactions_total",
    "Total count of settlement transactions processed by AntFlow Guard",
    ["status", "currency"],
)


def record_settlement_metric(status: str, currency: str) -> None:
    """Helper to record settlement business metric without modifying core ledger logic."""
    SETTLEMENT_TRANSACTIONS_TOTAL.labels(status=status, currency=currency).inc()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware that measures HTTP request rates, status codes, and durations.

    Uses route matching templates (e.g., '/api/v1/merchants/{merchant_id}/wallets')
    instead of raw request paths to avoid high-cardinality metric explosion.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Avoid circular instrumentation by skipping the metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Resolve route template to protect metric cardinality
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                endpoint = getattr(route, "path", endpoint)
                break

        start_time = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)
