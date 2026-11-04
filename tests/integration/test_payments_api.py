from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_idempotent_duplicate_requests(client):
    """Fire identical request 5 times in a row and assert wallet balance only increments once."""
    headers = {"X-Idempotency-Key": "tx-idempotency-key-test-999"}
    payload = {
        "merchant_id": "merch_gateway_01",
        "source_amount": "1000.0000",
        "source_currency": "CNY",
        "settled_currency": "MYR",
        "fx_rate": "0.648520",
    }

    # 1. First request: Should create transaction and credit wallet
    res1 = await client.post("/api/v1/payments/settle", json=payload, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["idempotent_replay"] is False
    assert data1["status"] == "SETTLED"
    expected_settled = Decimal("648.5200")
    assert Decimal(data1["settled_amount"]) == expected_settled
    assert Decimal(data1["new_wallet_balance"]) == expected_settled

    # 2. Replay 4 more times: Must return cached transaction without double crediting
    for i in range(4):
        res_replay = await client.post("/api/v1/payments/settle", json=payload, headers=headers)
        assert res_replay.status_code == 200
        data_replay = res_replay.json()
        assert data_replay["idempotent_replay"] is True
        assert data_replay["id"] == data1["id"]
        # Balance must remain exactly 648.5200, never doubling or incrementing
        assert Decimal(data_replay["new_wallet_balance"]) == expected_settled

    # 3. Verify reconciliation ledger confirms balance is 100% matched with 0 discrepancy
    rec_res = await client.get("/api/v1/merchants/merch_gateway_01/reconciliation?currency=MYR")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["is_balanced"] is True
    assert Decimal(rec_data["discrepancy"]) == Decimal("0.0000")
    assert Decimal(rec_data["wallet_balance"]) == expected_settled
    assert Decimal(rec_data["ledger_settled_total"]) == expected_settled
    assert rec_data["summary"]["total_transactions"] == 1


@pytest.mark.asyncio
async def test_high_risk_flagging_holds_wallet_credit(client):
    """High-risk transactions must be recorded with FLAGGED_HIGH_RISK and NOT credit merchant wallet."""
    headers = {"X-Idempotency-Key": "tx-suspicious-spike-001"}
    # Source amount * fx_rate > 50,000 threshold
    payload = {
        "merchant_id": "merch_flagged_01",
        "source_amount": "100000.0000",
        "source_currency": "USD",
        "settled_currency": "MYR",
        "fx_rate": "4.500000",
    }

    res = await client.post("/api/v1/payments/settle", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "FLAGGED_HIGH_RISK"
    assert data["risk_score"] >= 65
    # Balance must remain 0.0000 because funds are held under risk review
    assert Decimal(data["new_wallet_balance"]) == Decimal("0.0000")
