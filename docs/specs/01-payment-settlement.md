# Spec 01: Cross-Border Payment Settlement & Risk Triage Engine

- **Status:** APPROVED
- **Author:** Staff FinTech Architect & AI Agent
- **Target Microservice:** `AntFlow Guard`
- **Domain:** Cross-Border Merchant Settlement, Idempotency, and FX Volatility Control

---

## 1. Business Problem
Ant International connects global consumers (paying via local wallets like Touch 'n Go, GCash, KakaoPay, Alipay+) to cross-border merchants who require settlement in their local operating currency (MYR, SGD, USD).
To prevent severe financial loss:
1. Every payment mutation MUST be strictly idempotent. A merchant or buyer resending the same request over a flaky network connection must never be charged or credited twice.
2. Concurrent settlement payouts against a merchant wallet balance must be serialized using pessimistic row locking to prevent negative balances or double-spend race conditions.
3. Sub-cent accuracy must be maintained using Banker's Rounding (`ROUND_HALF_EVEN`) with zero floating-point arithmetic.
4. Sudden transaction volume spikes or extreme FX deviation must be flagged for risk triage before funds are credited.

---

## 2. API Endpoint Specification

### `POST /api/v1/payments/settle`

#### HTTP Headers
| Header | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `X-Idempotency-Key` | String (UUID or alphanumeric 16-128 chars) | Yes | Deduplication key for exactly-once processing. |
| `Content-Type` | `application/json` | Yes | Request payload format. |

#### Request Body (JSON)
```json
{
  "merchant_id": "merch_trx_kl_01",
  "source_amount": "1000.0000",
  "source_currency": "CNY",
  "settled_currency": "MYR",
  "fx_rate": "0.648520"
}
```

#### Constraints:
- `merchant_id`: String, length 3 to 64 chars.
- `source_amount`: Decimal, strictly > 0, up to 4 decimal places.
- `source_currency`: ISO 4217 3-letter currency code (e.g., CNY, USD, SGD).
- `settled_currency`: ISO 4217 3-letter currency code (e.g., MYR, SGD, USD).
- `fx_rate`: Decimal, strictly > 0, up to 6 decimal places.

---

## 3. State Machine & Lifecycle Transitions

```
[Incoming Request]
       │
       ▼
[Check Idempotency Key] ── (Key Exists) ──► Return Cached Transaction (idempotent_replay=True, HTTP 200)
       │ (Key New)
       ▼
[Acquire Merchant Wallet Row Lock (SELECT ... FOR UPDATE)]
       │
       ▼
[Compute Settled Amount (Banker's Rounding)]
  settled_amount = round_half_even(source_amount * fx_rate, 4)
       │
       ▼
[Run Heuristic & Anomaly Risk Triage]
  - If settled_amount > 50,000.0000 ──► Risk Score +65 (LARGE_SETTLEMENT_VOLUME_SPIKE)
  - If FX rate outside expected corridor [0.55, 0.75] for CNY/MYR ──► Risk Score +50 (FX_RATE_CORRIDOR_ANOMALY)
       │
       ├── (Risk Score >= 60) ──► Status: FLAGGED_HIGH_RISK (Hold balance update)
       │
       └── (Risk Score < 60)  ──► Status: SETTLED (Credit wallet balance)
       │
       ▼
[Insert Immutable Transaction Record]
       │
       ▼
[Commit Atomic Transaction & Return HTTP 200 Response]
```

---

## 4. Response Schema

```json
{
  "id": "a576e27a-8f55-46eb-816b-1361c4deee68",
  "idempotency_key": "tx-uniq-999",
  "merchant_id": "merch_trx_kl_01",
  "source_amount": "1000.0000",
  "source_currency": "CNY",
  "settled_amount": "648.5200",
  "settled_currency": "MYR",
  "fx_rate_applied": "0.648520",
  "status": "SETTLED",
  "risk_score": 0,
  "new_wallet_balance": "648.5200",
  "idempotent_replay": false
}
```

---

## 5. Error Codes & Edge Cases
| HTTP Status | Code / Condition | Mitigation |
| :--- | :--- | :--- |
| `400 Bad Request` | Missing `X-Idempotency-Key` or negative amounts | Pydantic v2 strict validation |
| `409 Conflict` | Concurrent in-flight requests with identical key | Database unique constraint with retry/fetch logic |
| `422 Unprocessable` | Invalid currency code or decimal format | Strict regex pattern matching |
