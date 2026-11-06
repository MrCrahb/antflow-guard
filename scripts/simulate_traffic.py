#!/usr/bin/env python3
"""AntFlow Guard — Live Observability & Anomaly Traffic Simulator

Generates realistic concurrent payment traffic to demonstrate live telemetry in Grafana:
1. Normal clean settlements (CNY -> MYR, SGD -> MYR)
2. High-value anomaly volume spikes (> 50,000 threshold) triggering risk triage
3. Idempotent replays testing duplicate deduplication
4. Currency lookups and healthchecks
"""

import asyncio
import random
import time
import uuid

import httpx

API_BASE_URL = "http://localhost:8000"

NORMAL_CORRIDORS = [
    ("CNY", "MYR", "0.6485"),
    ("SGD", "MYR", "3.4820"),
    ("USD", "MYR", "4.4500"),
]

MERCHANTS = [
    "merch_lazada_01",
    "merch_shopee_02",
    "merch_grab_sea_03",
    "merch_airasia_04",
]


async def simulate_clean_settlement(client: httpx.AsyncClient) -> None:
    source_curr, settled_curr, rate = random.choice(NORMAL_CORRIDORS)
    amount = f"{random.randint(50, 2500)}.0000"
    merchant_id = random.choice(MERCHANTS)
    tx_key = f"tx-live-{uuid.uuid4().hex[:12]}"

    payload = {
        "merchant_id": merchant_id,
        "source_amount": amount,
        "source_currency": source_curr,
        "settled_currency": settled_curr,
        "fx_rate": rate,
    }
    headers = {"X-Idempotency-Key": tx_key}

    try:
        res = await client.post(f"{API_BASE_URL}/api/v1/payments/settle", json=payload, headers=headers)
        if res.status_code == 200:
            print(f"  [SETTLED] {merchant_id}: {amount} {source_curr} -> {settled_curr} (HTTP {res.status_code})")
        else:
            print(f"  [ERROR] Clean settlement failed: HTTP {res.status_code} - {res.text}")
    except Exception as e:
        print(f"  [EXCEPTION] Clean settlement: {e}")


async def simulate_high_risk_spike(client: httpx.AsyncClient) -> None:
    # Large volume (> 50,000 threshold) triggering statistical risk score >= 65
    amount = f"{random.randint(60000, 150000)}.0000"
    merchant_id = random.choice(MERCHANTS)
    tx_key = f"tx-spike-{uuid.uuid4().hex[:12]}"

    payload = {
        "merchant_id": merchant_id,
        "source_amount": amount,
        "source_currency": "USD",
        "settled_currency": "MYR",
        "fx_rate": "4.5000",
    }
    headers = {"X-Idempotency-Key": tx_key}

    try:
        res = await client.post(f"{API_BASE_URL}/api/v1/payments/settle", json=payload, headers=headers)
        data = res.json()
        print(
            f"  ⚠️  [FLAGGED] High-Risk Spike: {amount} USD -> Score {data.get('risk_score', 'N/A')} (Status: {data.get('status')})"
        )
    except Exception as e:
        print(f"  [EXCEPTION] High risk spike: {e}")


async def simulate_idempotent_replay(client: httpx.AsyncClient) -> None:
    # Replays the exact same idempotency key 3 times
    tx_key = f"tx-replay-{uuid.uuid4().hex[:12]}"
    payload = {
        "merchant_id": "merch_lazada_01",
        "source_amount": "1200.0000",
        "source_currency": "CNY",
        "settled_currency": "MYR",
        "fx_rate": "0.6485",
    }
    headers = {"X-Idempotency-Key": tx_key}

    for i in range(3):
        res = await client.post(f"{API_BASE_URL}/api/v1/payments/settle", json=payload, headers=headers)
        data = res.json()
        replay_str = "REPLAY" if data.get("idempotent_replay") else "FIRST_SEEN"
        print(f"  🔄 [IDEMPOTENCY] Key {tx_key[-6:]} call {i+1}/3 -> {replay_str} (HTTP {res.status_code})")
        await asyncio.sleep(0.05)


async def simulate_read_traffic(client: httpx.AsyncClient) -> None:
    # Random health check or currency query
    endpoint = random.choice(["/health", "/api/v1/currencies"])
    res = await client.get(f"{API_BASE_URL}{endpoint}")
    print(f"  📊 [READ] {endpoint} -> HTTP {res.status_code}")


async def main(duration_seconds: int = 15):
    print("==========================================================")
    print("  🚀 AntFlow Guard — Live Traffic & Anomaly Generator")
    print(f"  Target: {API_BASE_URL} | Duration: {duration_seconds}s")
    print("==========================================================")

    async with httpx.AsyncClient(timeout=10.0) as client:
        start_time = time.time()
        batch = 1

        while (time.time() - start_time) < duration_seconds:
            print(f"\n--- Batch #{batch} (Elapsed: {int(time.time() - start_time)}s / {duration_seconds}s) ---")
            tasks = [
                simulate_clean_settlement(client),
                simulate_clean_settlement(client),
                simulate_clean_settlement(client),
                simulate_read_traffic(client),
            ]

            # Intermittently inject anomalies and idempotent bursts
            if batch % 2 == 0:
                tasks.append(simulate_high_risk_spike(client))
            if batch % 3 == 0:
                tasks.append(simulate_idempotent_replay(client))

            await asyncio.gather(*tasks)
            batch += 1
            await asyncio.sleep(1.0)

    print("\n==========================================================")
    print("  ✅ Simulation complete! Check your Grafana dashboard:")
    print("  👉 http://localhost:3001/d/antflow-sre-dash/antflow-guard-e28094-sre-operational-dashboard")
    print("==========================================================")


if __name__ == "__main__":
    import sys

    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    asyncio.run(main(duration))
