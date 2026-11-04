import uuid
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PaymentSettlementRequest(BaseModel):
    merchant_id: str = Field(
        ..., min_length=3, max_length=64, examples=["merch_trx_kl_01"]
    )
    source_amount: Decimal = Field(
        ..., gt=Decimal("0.00"), decimal_places=4, examples=[Decimal("1000.0000")]
    )
    source_currency: str = Field(..., pattern="^[A-Z]{3}$", examples=["CNY"])
    settled_currency: str = Field(..., pattern="^[A-Z]{3}$", examples=["MYR"])
    fx_rate: Decimal = Field(..., gt=Decimal("0.00"), examples=[Decimal("0.648520")])


class PaymentSettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    idempotency_key: str
    merchant_id: str
    source_amount: Decimal
    source_currency: str
    settled_amount: Decimal
    settled_currency: str
    fx_rate_applied: Decimal
    status: str
    risk_score: int
    new_wallet_balance: Decimal
    idempotent_replay: bool = False


class MerchantWalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: str
    currency: str
    balance: Decimal
    version: int


class ReconciliationSummary(BaseModel):
    total_transactions: int
    settled_count: int
    flagged_count: int
    total_settled_volume: Decimal
    currency: str


class ReconciliationResponse(BaseModel):
    merchant_id: str
    currency: str
    wallet_balance: Decimal
    ledger_settled_total: Decimal
    discrepancy: Decimal
    is_balanced: bool
    summary: ReconciliationSummary
