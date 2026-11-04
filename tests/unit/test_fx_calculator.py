from decimal import Decimal
from hypothesis import given, settings, strategies as st
import pytest

from app.services.settlement import calculate_settled_amount, evaluate_transaction_risk
from app.services.fx_service import get_live_fx_rate, SUPPORTED_CURRENCIES
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

    # Invariant 2: Result must be non-negative
    assert settled >= Decimal("0.0000")

    # Invariant 3: Result must strictly adhere to 4 decimal places of sub-cent precision
    assert settled == settled.quantize(FOUR_PLACES)
    assert not settled.is_nan()
    assert not settled.is_infinite()


def test_bankers_rounding_half_even():
    """Verify Banker's Rounding (ROUND_HALF_EVEN) prevents statistical upward bias."""
    rate_down = Decimal("0.00025")
    rate_up = Decimal("0.00035")
    one = Decimal("1.0000")

    assert calculate_settled_amount(one, rate_down) == Decimal("0.0002")
    assert calculate_settled_amount(one, rate_up) == Decimal("0.0004")


def test_risk_evaluation_dynamic_market_divergence():
    """Verify risk engine catches excessive volume and dynamic market rate slippage."""
    # Case 1: Normal transaction with fair market rate
    req_normal = PaymentSettlementRequest(
        merchant_id="merch_01",
        source_amount=Decimal("100.0000"),
        source_currency="CNY",
        settled_currency="MYR",
        fx_rate=Decimal("0.608500"),
    )
    score, meta = evaluate_transaction_risk(req_normal, Decimal("60.8500"), market_rate=Decimal("0.608500"))
    assert score == 0
    assert len(meta["flags"]) == 0

    # Case 2: Extreme market divergence (> 10% slippage)
    req_bad_fx = PaymentSettlementRequest(
        merchant_id="merch_01",
        source_amount=Decimal("100.0000"),
        source_currency="CNY",
        settled_currency="MYR",
        fx_rate=Decimal("0.850000"),  # >39% above market rate 0.6085
    )
    score, meta = evaluate_transaction_risk(req_bad_fx, Decimal("85.0000"), market_rate=Decimal("0.608500"))
    assert score >= 60
    assert any("FX_MARKET_DIVERGENCE" in flag for flag in meta["flags"])


@pytest.mark.asyncio
async def test_live_fx_service_supported_currencies():
    """Verify multi-currency support and fallback rates."""
    assert "MYR" in SUPPORTED_CURRENCIES
    assert "SGD" in SUPPORTED_CURRENCIES
    assert "CNY" in SUPPORTED_CURRENCIES
    assert "IDR" in SUPPORTED_CURRENCIES
    assert "PHP" in SUPPORTED_CURRENCIES
    assert "THB" in SUPPORTED_CURRENCIES
    assert "KRW" in SUPPORTED_CURRENCIES
    assert "USD" in SUPPORTED_CURRENCIES

    rate = await get_live_fx_rate("CNY", "MYR")
    assert isinstance(rate, Decimal)
    assert rate > Decimal("0")
