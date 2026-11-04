import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, JSON, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Wallet(Base):
    """Merchant wallet ledger balance with optimistic/pessimistic lock semantics."""

    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("merchant_id", "currency", name="uq_wallet_merchant_currency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)  # e.g., "MYR", "SGD", "USD"
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Transaction(Base):
    """Core transaction ledger storing immutable cross-border settlement events."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    merchant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_applied: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    settled_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    settled_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "SETTLED", "FLAGGED_HIGH_RISK", "REJECTED"
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    audit_logs: Mapped[list["RiskAuditLog"]] = relationship(
        "RiskAuditLog", back_populates="transaction", lazy="selectin"
    )


class RiskAuditLog(Base):
    """Stores explainable risk triage results and agent triage records."""

    __tablename__ = "risk_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id"), index=True, nullable=False
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    anomaly_reason: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    reviewed_by_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="audit_logs"
    )
