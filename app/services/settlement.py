import asyncio
import time
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger import RiskAuditLog, Transaction, Wallet
from app.schemas.payment import PaymentSettlementRequest, PaymentSettlementResponse
from app.services.fx_service import get_live_fx_rate

FOUR_PLACES = Decimal("0.0001")

# In-memory synchronization lock per merchant/currency to support engines without native row-level locking
_wallet_memory_locks: Dict[Tuple[str, str], asyncio.Lock] = defaultdict(asyncio.Lock)


def calculate_settled_amount(source_amount: Decimal, fx_rate: Decimal) -> Decimal:
    """Pure function for deterministic financial rounding using Banker's Rounding (ROUND_HALF_EVEN)."""
    raw_settled = source_amount * fx_rate
    return raw_settled.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)


def evaluate_transaction_risk(
    payload: PaymentSettlementRequest,
    settled_amount: Decimal,
    market_rate: Optional[Decimal] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Deterministic heuristic + statistical threshold check for cross-border anomalies."""
    risk_score = 0
    reasons = []

    # Rule 1: High-value cross-border single settlement threshold (> 50,000)
    if settled_amount > Decimal("50000.0000"):
        risk_score += 65
        reasons.append("LARGE_SETTLEMENT_VOLUME_SPIKE")

    # Rule 2: Dynamic FX market divergence and slippage anomaly
    if market_rate is not None and market_rate > Decimal("0"):
        # Calculate percentage deviation from the real-time interbank market rate
        deviation = abs(payload.fx_rate - market_rate) / market_rate
        if deviation > Decimal("0.10"):  # Greater than 10% deviation from interbank market
            risk_score += 60
            pct_str = f"{float(deviation * 100):.1f}%"
            reasons.append(f"FX_MARKET_DIVERGENCE_ANOMALY (Deviation: {pct_str})")
    else:
        # Static fallback corridor check for CNY -> MYR
        if payload.source_currency == "CNY" and payload.settled_currency == "MYR":
            if not (Decimal("0.550000") <= payload.fx_rate <= Decimal("0.750000")):
                risk_score += 50
                reasons.append("FX_RATE_CORRIDOR_ANOMALY")

    return min(risk_score, 100), {"flags": reasons}


async def settle_cross_border_payment(
    session: AsyncSession,
    idempotency_key: str,
    payload: PaymentSettlementRequest,
) -> PaymentSettlementResponse:
    """Executes atomic cross-border settlement with idempotency deduplication and pessimistic locking."""
    start_time = time.perf_counter()
    lock_key = (payload.merchant_id, payload.settled_currency)

    async with _wallet_memory_locks[lock_key]:
        try:
            async with session.begin():
                # Step 1: Pre-check Idempotency Key
                existing_tx_stmt = select(Transaction).where(
                    Transaction.idempotency_key == idempotency_key
                )
                existing_tx = (await session.execute(existing_tx_stmt)).scalar_one_or_none()

                if existing_tx:
                    wallet_stmt = select(Wallet).where(
                        Wallet.merchant_id == payload.merchant_id,
                        Wallet.currency == payload.settled_currency,
                    )
                    wallet = (await session.execute(wallet_stmt)).scalar_one_or_none()
                    current_balance = wallet.balance if wallet else Decimal("0.0000")

                    return PaymentSettlementResponse(
                        id=existing_tx.id,
                        idempotency_key=existing_tx.idempotency_key,
                        merchant_id=existing_tx.merchant_id,
                        source_amount=existing_tx.source_amount,
                        source_currency=existing_tx.source_currency,
                        settled_amount=existing_tx.settled_amount,
                        settled_currency=existing_tx.settled_currency,
                        fx_rate_applied=existing_tx.fx_rate_applied,
                        status=existing_tx.status,
                        risk_score=existing_tx.risk_score,
                        new_wallet_balance=current_balance,
                        idempotent_replay=True,
                    )

                # Step 2: Acquire Pessimistic Row-Level Lock on Merchant's Wallet
                wallet_lock_stmt = (
                    select(Wallet)
                    .where(
                        Wallet.merchant_id == payload.merchant_id,
                        Wallet.currency == payload.settled_currency,
                    )
                    .with_for_update()
                )
                wallet = (await session.execute(wallet_lock_stmt)).scalar_one_or_none()

                if not wallet:
                    wallet = Wallet(
                        merchant_id=payload.merchant_id,
                        currency=payload.settled_currency,
                        balance=Decimal("0.0000"),
                        version=1,
                    )
                    session.add(wallet)
                    await session.flush()

                # Step 3: Compute FX Settlement & Run Risk Triage
                settled_amount = calculate_settled_amount(payload.source_amount, payload.fx_rate)

                # Fetch real-time market benchmark rate for dynamic anomaly evaluation
                market_rate = await get_live_fx_rate(
                    payload.source_currency, payload.settled_currency
                )
                risk_score, risk_meta = evaluate_transaction_risk(
                    payload, settled_amount, market_rate=market_rate
                )
                status = "FLAGGED_HIGH_RISK" if risk_score >= 60 else "SETTLED"

                # Only credit wallet balance if settlement is clean
                if status == "SETTLED":
                    wallet.balance = (wallet.balance + settled_amount).quantize(
                        FOUR_PLACES, rounding=ROUND_HALF_EVEN
                    )
                    wallet.version += 1

                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                # Step 4: Record Immutable Ledger Entry & Risk Audit
                new_tx = Transaction(
                    idempotency_key=idempotency_key,
                    merchant_id=payload.merchant_id,
                    source_amount=payload.source_amount,
                    source_currency=payload.source_currency,
                    fx_rate_applied=payload.fx_rate,
                    settled_amount=settled_amount,
                    settled_currency=payload.settled_currency,
                    status=status,
                    risk_score=risk_score,
                    risk_metadata=risk_meta,
                    latency_ms=elapsed_ms,
                )
                session.add(new_tx)
                await session.flush()

                if risk_score > 0:
                    audit_log = RiskAuditLog(
                        transaction_id=new_tx.id,
                        risk_score=risk_score,
                        anomaly_reason=risk_meta,
                        reviewed_by_agent=False,
                    )
                    session.add(audit_log)
                    await session.flush()

                return PaymentSettlementResponse(
                    id=new_tx.id,
                    idempotency_key=new_tx.idempotency_key,
                    merchant_id=new_tx.merchant_id,
                    source_amount=new_tx.source_amount,
                    source_currency=new_tx.source_currency,
                    settled_amount=new_tx.settled_amount,
                    settled_currency=new_tx.settled_currency,
                    fx_rate_applied=new_tx.fx_rate_applied,
                    status=new_tx.status,
                    risk_score=new_tx.risk_score,
                    new_wallet_balance=wallet.balance,
                    idempotent_replay=False,
                )

        except IntegrityError:
            # Step 5: Graceful Race-Condition Handling
            for attempt in range(5):
                await asyncio.sleep(0.05 * (attempt + 1))
                async with session.begin():
                    existing_tx = (
                        await session.execute(
                            select(Transaction).where(
                                Transaction.idempotency_key == idempotency_key
                            )
                        )
                    ).scalar_one_or_none()

                    if existing_tx:
                        wallet = (
                            await session.execute(
                                select(Wallet).where(
                                    Wallet.merchant_id == payload.merchant_id,
                                    Wallet.currency == payload.settled_currency,
                                )
                            )
                        ).scalar_one()

                        return PaymentSettlementResponse(
                            id=existing_tx.id,
                            idempotency_key=existing_tx.idempotency_key,
                            merchant_id=existing_tx.merchant_id,
                            source_amount=existing_tx.source_amount,
                            source_currency=existing_tx.source_currency,
                            settled_amount=existing_tx.settled_amount,
                            settled_currency=existing_tx.settled_currency,
                            fx_rate_applied=existing_tx.fx_rate_applied,
                            status=existing_tx.status,
                            risk_score=existing_tx.risk_score,
                            new_wallet_balance=wallet.balance,
                            idempotent_replay=True,
                        )

            raise
