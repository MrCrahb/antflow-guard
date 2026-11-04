from decimal import Decimal
from hypothesis import given, settings, strategies as st

from app.services.settlement import calculate_settled_amount, evaluate_transaction_risk
from app.schemas.payment import PaymentSettlementRequest

FOUR_PLACES = Decimal("0.0001")


@given(
    amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000.00"), places=4),
    fx_rate=st.decimals(min_value=Decimal("0.000001"), max_value=Decimal("100.000000"), places=6),
)
@settings(max_examples=500, deadline=None)
def test_hypothesis_calculate_settled_amount_financial_precision(amount: Decimal, fx_rate: Decimal):
    """Property-based test throwing 500 randomized financial inputs to verify precision invariants."""
    settled = calculate_settled_amount(amount, fx_rate)

    # Invariant 1: Result must be a Decimal
    assert isinstance(settled, Decimal)

    # Invariant 2: Result must be non-negative (can be 0.0000 for sub-cent micro amounts)
    assert settled >= Decimal("0.0000")

    # Invariant 3: Result must strictly adhere to 4 decimal places of sub-cent precision
    assert settled == settled.quantize(FOUR_PLACES)
    assert not settled.is_nan()
    assert not settled.is_infinite()


def test_bankers_rounding_half_even():
    """Verify Banker's Rounding (ROUND_HALF_EVEN) prevents statistical upward bias."""
    # 2.5 rounds to 2 (even), 3.5 rounds to 4 (even)
    rate_down = Decimal("0.00025")
    rate_up = Decimal("0.00035")
    one = Decimal("1.0000")

    assert calculate_settled_amount(one, rate_down) == Decimal("0.0002")
    assert calculate_settled_amount(one, rate_up) == Decimal("0.0004")


def test_risk_evaluation_corridor_and_volume():
    """Verify risk engine catches excessive volume and corridor deviations."""
    # Case 1: Normal transaction
    req_normal = PaymentSettlementRequest(
        merchant_id="merch_01",
        source_amount=Decimal("100.0000"),
        source_currency="CNY",
        settled_currency="MYR",
        fx_rate=Decimal("0.650000"),
    )
    score, meta = evaluate_transaction_risk(req_normal, Decimal("65.0000"))
    assert score == 0
    assert len(meta["flags"]) == 0

    # Case 2: High volume spike (> 50,000 settled)
    req_high_volume = PaymentSettlementRequest(
        merchant_id="merch_01",
        source_amount=Decimal("100000.0000"),
        source_currency="USD",
        settled_currency="MYR",
        fx_rate=Decimal("4.500000"),
    )
    score, meta = evaluate_transaction_risk(req_high_volume, Decimal("450000.0000"))
    assert score >= 65
    assert "LARGE_SETTLEMENT_VOLUME_SPIKE" in meta["flags"]

    # Case 3: Abnormal CNY -> MYR FX rate deviation
    req_fx_anomaly = PaymentSettlementRequest(
        merchant_id="merch_01",
        source_amount=Decimal("1000.0000"),
        source_currency="CNY",
        settled_currency="MYR",
        fx_rate=Decimal("0.900000"),  # Outside [0.55, 0.75]
    )
    score, meta = evaluate_transaction_risk(req_fx_anomaly, Decimal("900.0000"))
    assert score >= 50
    assert "FX_RATE_CORRIDOR_ANOMALY" in meta["flags"]
