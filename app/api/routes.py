from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ledger import Transaction, Wallet
from app.schemas.payment import (
    MerchantWalletResponse,
    PaymentSettlementRequest,
    PaymentSettlementResponse,
    ReconciliationResponse,
    ReconciliationSummary,
)
from app.services.settlement import settle_cross_border_payment

router = APIRouter(prefix="/api/v1", tags=["Cross-Border Settlement"])


@router.post(
    "/payments/settle",
    response_model=PaymentSettlementResponse,
    status_code=status.HTTP_200_OK,
    summary="Settle Cross-Border Payment",
    description="Idempotent cross-border payment settlement engine enforcing pessimistic locking and risk triage.",
)
async def post_payment_settle(
    payload: PaymentSettlementRequest,
    x_idempotency_key: str = Header(
        ...,
        alias="X-Idempotency-Key",
        min_length=8,
        max_length=128,
        description="Mandatory idempotency key ensuring exactly-once processing.",
    ),
    session: AsyncSession = Depends(get_db),
) -> PaymentSettlementResponse:
    try:
        return await settle_cross_border_payment(
            session=session,
            idempotency_key=x_idempotency_key,
            payload=payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Settlement execution failed: {str(exc)}",
        )


@router.get(
    "/merchants/{merchant_id}/wallets",
    response_model=List[MerchantWalletResponse],
    summary="List Merchant Wallets",
)
async def get_merchant_wallets(
    merchant_id: str,
    session: AsyncSession = Depends(get_db),
) -> List[MerchantWalletResponse]:
    stmt = select(Wallet).where(Wallet.merchant_id == merchant_id)
    result = await session.execute(stmt)
    wallets = result.scalars().all()
    return list(wallets)


@router.get(
    "/merchants/{merchant_id}/reconciliation",
    response_model=ReconciliationResponse,
    summary="Daily Settlement Ledger Reconciliation",
    description="Generates a settlement summary comparing wallet balances against immutable transaction entries.",
)
async def get_merchant_reconciliation(
    merchant_id: str,
    currency: str = Query("MYR", pattern="^[A-Z]{3}$"),
    session: AsyncSession = Depends(get_db),
) -> ReconciliationResponse:
    # 1. Fetch current wallet balance
    wallet_stmt = select(Wallet).where(
        Wallet.merchant_id == merchant_id,
        Wallet.currency == currency,
    )
    wallet = (await session.execute(wallet_stmt)).scalar_one_or_none()
    current_balance = wallet.balance if wallet else Decimal("0.0000")

    # 2. Compute ledger aggregate sums
    tx_stmt = select(
        func.count(Transaction.id).label("total_count"),
        func.coalesce(
            func.sum(
                case((Transaction.status == "SETTLED", Transaction.settled_amount), else_=0)
            ),
            0,
        ).label("settled_sum"),
        func.coalesce(
            func.sum(case((Transaction.status == "FLAGGED_HIGH_RISK", 1), else_=0)),
            0,
        ).label("flagged_count"),
        func.coalesce(
            func.sum(case((Transaction.status == "SETTLED", 1), else_=0)),
            0,
        ).label("settled_count"),
    ).where(
        Transaction.merchant_id == merchant_id,
        Transaction.settled_currency == currency,
    )

    agg = (await session.execute(tx_stmt)).one()

    total_count = int(agg.total_count or 0)
    settled_sum = Decimal(str(agg.settled_sum or "0.0000"))
    flagged_count = int(agg.flagged_count or 0)
    settled_count = int(agg.settled_count or 0)

    discrepancy = (current_balance - settled_sum).quantize(Decimal("0.0001"))
    is_balanced = discrepancy == Decimal("0.0000")

    return ReconciliationResponse(
        merchant_id=merchant_id,
        currency=currency,
        wallet_balance=current_balance,
        ledger_settled_total=settled_sum,
        discrepancy=discrepancy,
        is_balanced=is_balanced,
        summary=ReconciliationSummary(
            total_transactions=total_count,
            settled_count=settled_count,
            flagged_count=flagged_count,
            total_settled_volume=settled_sum,
            currency=currency,
        ),
    )


@router.get(
    "/transactions",
    summary="List Recent Settlement Transactions",
)
async def list_transactions(
    limit: int = Query(50, ge=1, le=200),
    merchant_id: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    if merchant_id:
        stmt = stmt.where(Transaction.merchant_id == merchant_id)
    result = await session.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": str(tx.id),
            "idempotency_key": tx.idempotency_key,
            "merchant_id": tx.merchant_id,
            "source_amount": str(tx.source_amount),
            "source_currency": tx.source_currency,
            "settled_amount": str(tx.settled_amount),
            "settled_currency": tx.settled_currency,
            "fx_rate_applied": str(tx.fx_rate_applied),
            "status": tx.status,
            "risk_score": tx.risk_score,
            "latency_ms": tx.latency_ms,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        }
        for tx in records
    ]
