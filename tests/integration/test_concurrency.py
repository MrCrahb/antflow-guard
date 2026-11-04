import asyncio
import uuid
from decimal import Decimal
import pytest
from app.models.ledger import Wallet
from tests.conftest import TestingSessionLocal


async def seed_merchant_wallet(merchant_id: str, currency: str, initial_balance: Decimal = Decimal("0.0000")):
    """Helper to provision merchant wallet before concurrency test suites."""
    async with TestingSessionLocal() as session:
        async with session.begin():
            wallet = Wallet(
                merchant_id=merchant_id,
                currency=currency,
                balance=initial_balance,
                version=1,
            )
            session.add(wallet)


@pytest.mark.asyncio
async def test_concurrent_identical_idempotency_keys(client):
    """Simulate extreme race condition: 10 concurrent requests arrive at the exact same millisecond

    with the same new idempotency key.
    Enforces that our IntegrityError recovery handles the race condition smoothly,
    yielding 200 OK for all 10 requests, with exactly ONE credit to the ledger.
    """
    merchant_id = "merch_race_test_01"
    await seed_merchant_wallet(merchant_id, "MYR")

    idempotency_key = f"tx-concurrent-race-{uuid.uuid4()}"
    payload = {
        "merchant_id": merchant_id,
        "source_amount": "500.0000",
        "source_currency": "CNY",
        "settled_currency": "MYR",
        "fx_rate": "0.648500",
    }
    headers = {"X-Idempotency-Key": idempotency_key}

    # Fire 10 simultaneous requests
    tasks = [client.post("/api/v1/payments/settle", json=payload, headers=headers) for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    # All responses must succeed with 200 OK (no 500 Internal Server Errors!)
    for res in responses:
        assert res.status_code == 200, f"Failed with {res.status_code}: {res.text}"

    data_list = [res.json() for res in responses]
    replays = [d for d in data_list if d["idempotent_replay"] is True]
    initials = [d for d in data_list if d["idempotent_replay"] is False]

    # Exactly 1 primary settlement and 9 idempotent replays
    assert len(initials) == 1
    assert len(replays) == 9

    # Expected settled: 500 * 0.6485 = 324.2500
    expected_credit = Decimal("324.2500")

    # Check merchant wallet
    rec_res = await client.get(f"/api/v1/merchants/{merchant_id}/reconciliation?currency=MYR")
    rec_data = rec_res.json()
    assert Decimal(rec_data["wallet_balance"]) == expected_credit
    assert Decimal(rec_data["ledger_settled_total"]) == expected_credit
    assert rec_data["summary"]["total_transactions"] == 1


@pytest.mark.asyncio
async def test_concurrent_multiple_settlements_no_lost_updates(client):
    """Fire 15 distinct settlements concurrently against the same merchant wallet.

    Pessimistic row locking ensures sequential atomic balance mutations without lost updates.
    """
    merchant_id = "merch_concurrent_volume_01"
    await seed_merchant_wallet(merchant_id, "MYR")

    settle_amount = Decimal("100.0000")
    fx_rate = Decimal("0.650000")
    single_settled = Decimal("65.0000")
    num_requests = 15

    tasks = []
    for i in range(num_requests):
        headers = {"X-Idempotency-Key": f"tx-multi-load-{uuid.uuid4()}"}
        payload = {
            "merchant_id": merchant_id,
            "source_amount": str(settle_amount),
            "source_currency": "CNY",
            "settled_currency": "MYR",
            "fx_rate": str(fx_rate),
        }
        tasks.append(client.post("/api/v1/payments/settle", json=payload, headers=headers))

    responses = await asyncio.gather(*tasks)

    for res in responses:
        assert res.status_code == 200

    expected_total_balance = single_settled * num_requests  # 65.0000 * 15 = 975.0000

    rec_res = await client.get(f"/api/v1/merchants/{merchant_id}/reconciliation?currency=MYR")
    rec_data = rec_res.json()

    assert Decimal(rec_data["wallet_balance"]) == expected_total_balance
    assert Decimal(rec_data["ledger_settled_total"]) == expected_total_balance
    assert rec_data["is_balanced"] is True
    assert rec_data["summary"]["settled_count"] == num_requests
