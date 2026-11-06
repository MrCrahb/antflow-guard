import pytest
from httpx import ASGITransport, AsyncClient

from app.core.metrics import (
    HTTP_REQUESTS_TOTAL,
    SETTLEMENT_TRANSACTIONS_TOTAL,
    record_settlement_metric,
)
from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_exposed():
    """Verify that /metrics endpoint returns HTTP 200 and Prometheus exposition format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Trigger an endpoint to generate at least one metric sample
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200

        # Now fetch /metrics
        metrics_resp = await client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "text/plain" in metrics_resp.headers.get("content-type", "")

        metrics_text = metrics_resp.text
        # Assert custom metrics exist in the scraped text
        assert "antflow_http_requests_total" in metrics_text
        assert "antflow_http_request_duration_seconds" in metrics_text
        assert "antflow_settlement_transactions_total" in metrics_text


@pytest.mark.asyncio
async def test_http_requests_metric_increment():
    """Verify that PrometheusMiddleware correctly tracks request count and latency."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        before_count = HTTP_REQUESTS_TOTAL.labels(
            method="GET",
            endpoint="/health",
            status="200",
        )._value.get()

        res = await client.get("/health")
        assert res.status_code == 200

        after_count = HTTP_REQUESTS_TOTAL.labels(
            method="GET",
            endpoint="/health",
            status="200",
        )._value.get()

        assert after_count == before_count + 1


def test_settlement_business_metric():
    """Verify that record_settlement_metric records settled and flagged metrics correctly."""
    before_settled = SETTLEMENT_TRANSACTIONS_TOTAL.labels(
        status="SETTLED",
        currency="MYR",
    )._value.get()

    before_flagged = SETTLEMENT_TRANSACTIONS_TOTAL.labels(
        status="FLAGGED_HIGH_RISK",
        currency="MYR",
    )._value.get()

    record_settlement_metric(status="SETTLED", currency="MYR")
    record_settlement_metric(status="FLAGGED_HIGH_RISK", currency="MYR")

    after_settled = SETTLEMENT_TRANSACTIONS_TOTAL.labels(
        status="SETTLED",
        currency="MYR",
    )._value.get()

    after_flagged = SETTLEMENT_TRANSACTIONS_TOTAL.labels(
        status="FLAGGED_HIGH_RISK",
        currency="MYR",
    )._value.get()

    assert after_settled == before_settled + 1
    assert after_flagged == before_flagged + 1
