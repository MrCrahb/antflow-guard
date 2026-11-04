"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Send,
  CheckCircle2,
  TrendingUp,
  Wallet,
  Activity,
  Layers,
  ArrowRightLeft,
} from "lucide-react";

interface Transaction {
  id: string;
  idempotency_key: string;
  merchant_id: string;
  source_amount: string;
  source_currency: string;
  settled_amount: string;
  settled_currency: string;
  fx_rate_applied: string;
  status: string;
  risk_score: number;
  latency_ms: number;
  created_at: string;
}

interface Reconciliation {
  merchant_id: string;
  currency: string;
  wallet_balance: string;
  ledger_settled_total: string;
  discrepancy: string;
  is_balanced: boolean;
  summary: {
    total_transactions: number;
    settled_count: number;
    flagged_count: number;
    total_settled_volume: string;
    currency: string;
  };
}

export default function Dashboard() {
  const [backendUrl] = useState("http://localhost:8000");
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [reconciliation, setReconciliation] = useState<Reconciliation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State for Payment Simulation
  const [merchantId, setMerchantId] = useState("merch_trx_kl_01");
  const [sourceAmount, setSourceAmount] = useState("1000.0000");
  const [sourceCurrency, setSourceCurrency] = useState("CNY");
  const [settledCurrency, setSettledCurrency] = useState("MYR");
  const [fxRate, setFxRate] = useState("0.648520");
  const [idempotencyKey, setIdempotencyKey] = useState("tx-" + Date.now());
  const [lastResponse, setLastResponse] = useState<any>(null);

  const fetchDashboardData = async () => {
    try {
      const txRes = await fetch(`${backendUrl}/api/v1/transactions?limit=20`);
      if (txRes.ok) {
        const txData = await txRes.json();
        setTransactions(txData);
      }

      const recRes = await fetch(
        `${backendUrl}/api/v1/merchants/${merchantId}/reconciliation?currency=${settledCurrency}`
      );
      if (recRes.ok) {
        const recData = await recRes.json();
        setReconciliation(recData);
      }
    } catch (err: any) {
      console.warn("Backend not yet connected:", err.message);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000);
    return () => clearInterval(interval);
  }, [merchantId, settledCurrency]);

  const handleSimulatePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setLastResponse(null);

    try {
      const response = await fetch(`${backendUrl}/api/v1/payments/settle`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({
          merchant_id: merchantId,
          source_amount: sourceAmount,
          source_currency: sourceCurrency,
          settled_currency: settledCurrency,
          fx_rate: fxRate,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Payment settlement failed");
      }
      setLastResponse(data);
      await fetchDashboardData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const generateNewKey = () => {
    setIdempotencyKey("tx-" + Math.random().toString(36).substring(2, 10) + "-" + Date.now());
  };

  return (
    <div className="min-h-screen bg-[#070d1e] text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-[#0d162d]/80 backdrop-blur sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-blue-600 p-2 rounded-lg text-white shadow-lg shadow-blue-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              AntFlow Guard
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                TRX Engine v1.0
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              Cross-Border Settlement, Falcon FX Routing & AI Anomaly Triage
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-xs bg-slate-800/60 px-3 py-1.5 rounded-full border border-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-300">FastAPI Async Engine (Port 8000)</span>
          </div>
          <button
            onClick={fetchDashboardData}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
            title="Refresh Ledger"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className="p-6 max-w-7xl mx-auto w-full space-y-6 flex-1">
        {/* KPI Row */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[#111c38] border border-slate-800 rounded-xl p-5 shadow-sm">
            <div className="flex justify-between items-start text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
              <span>Merchant Balance</span>
              <Wallet className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-mono font-bold text-white">
              {reconciliation?.wallet_balance || "0.0000"} {settledCurrency}
            </div>
            <div className="text-xs text-emerald-400 mt-2 flex items-center gap-1 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Pessimistic Row-Locked
            </div>
          </div>

          <div className="bg-[#111c38] border border-slate-800 rounded-xl p-5 shadow-sm">
            <div className="flex justify-between items-start text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
              <span>Settled Volume</span>
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-mono font-bold text-emerald-400">
              {reconciliation?.ledger_settled_total || "0.0000"} {settledCurrency}
            </div>
            <div className="text-xs text-slate-400 mt-2">
              {reconciliation?.summary.settled_count || 0} Clean Settlements
            </div>
          </div>

          <div className="bg-[#111c38] border border-slate-800 rounded-xl p-5 shadow-sm">
            <div className="flex justify-between items-start text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
              <span>Risk & Slippage Flags</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-mono font-bold text-amber-400">
              {reconciliation?.summary.flagged_count || 0}
            </div>
            <div className="text-xs text-slate-400 mt-2">Auto-Held for Review</div>
          </div>

          <div className="bg-[#111c38] border border-slate-800 rounded-xl p-5 shadow-sm">
            <div className="flex justify-between items-start text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
              <span>Ledger Discrepancy</span>
              <Layers className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-mono font-bold text-purple-300">
              {reconciliation?.discrepancy || "0.0000"}
            </div>
            <div className="text-xs text-emerald-400 mt-2 flex items-center gap-1 font-medium">
              {reconciliation?.is_balanced ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  100% Sub-Cent Reconciled
                </>
              ) : (
                <span className="text-amber-400">Unbalanced Variance</span>
              )}
            </div>
          </div>
        </div>

        {/* Content Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Simulator Form */}
          <div className="bg-[#111c38] border border-slate-800 rounded-xl p-6 shadow-sm">
            <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-4">
              <ArrowRightLeft className="w-4 h-4 text-blue-400" />
              Settle Payment Simulation
            </h2>

            <form onSubmit={handleSimulatePayment} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Merchant ID
                </label>
                <input
                  type="text"
                  value={merchantId}
                  onChange={(e) => setMerchantId(e.target.value)}
                  className="w-full bg-[#0a1226] border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:border-blue-500 outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Source Amount
                  </label>
                  <input
                    type="text"
                    value={sourceAmount}
                    onChange={(e) => setSourceAmount(e.target.value)}
                    className="w-full bg-[#0a1226] border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:border-blue-500 outline-none"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Source Currency
                  </label>
                  <select
                    value={sourceCurrency}
                    onChange={(e) => setSourceCurrency(e.target.value)}
                    className="w-full bg-[#0a1226] border border-slate-700 rounded-lg px-3 py-2 text-white focus:border-blue-500 outline-none"
                  >
                    <option value="CNY">CNY (Alipay+)</option>
                    <option value="USD">USD (WorldFirst)</option>
                    <option value="SGD">SGD</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Settled Currency
                  </label>
                  <input
                    type="text"
                    value={settledCurrency}
                    readOnly
                    className="w-full bg-[#0a1226]/50 border border-slate-800 rounded-lg px-3 py-2 text-slate-400 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    FX Rate Applied
                  </label>
                  <input
                    type="text"
                    value={fxRate}
                    onChange={(e) => setFxRate(e.target.value)}
                    className="w-full bg-[#0a1226] border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:border-blue-500 outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-slate-400">
                    X-Idempotency-Key
                  </label>
                  <button
                    type="button"
                    onClick={generateNewKey}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Generate New
                  </button>
                </div>
                <input
                  type="text"
                  value={idempotencyKey}
                  onChange={(e) => setIdempotencyKey(e.target.value)}
                  className="w-full bg-[#0a1226] border border-slate-700 rounded-lg px-3 py-2 text-white font-mono text-xs focus:border-blue-500 outline-none"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2 transition disabled:opacity-50 mt-2"
              >
                {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Execute Atomic Settlement
              </button>
            </form>

            {/* Response Banner */}
            {lastResponse && (
              <div
                className={`mt-4 p-3.5 rounded-lg border text-xs font-mono space-y-1 ${
                  lastResponse.idempotent_replay
                    ? "bg-purple-950/40 border-purple-800/60 text-purple-200"
                    : lastResponse.status === "FLAGGED_HIGH_RISK"
                    ? "bg-amber-950/40 border-amber-800/60 text-amber-200"
                    : "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
                }`}
              >
                <div className="font-bold flex items-center justify-between">
                  <span>
                    Status: {lastResponse.status}
                    {lastResponse.idempotent_replay && " (IDEMPOTENT REPLAY)"}
                  </span>
                  <span>Risk Score: {lastResponse.risk_score}</span>
                </div>
                <div>Settled: {lastResponse.settled_amount} {lastResponse.settled_currency}</div>
                <div>New Balance: {lastResponse.new_wallet_balance} {lastResponse.settled_currency}</div>
              </div>
            )}

            {error && (
              <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-800/60 text-red-200 text-xs">
                {error}
              </div>
            )}
          </div>

          {/* Live Transaction Ledger Table */}
          <div className="lg:col-span-2 bg-[#111c38] border border-slate-800 rounded-xl p-6 shadow-sm flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Activity className="w-4 h-4 text-blue-400" />
                Live Cross-Border Settlement Feed
              </h2>
              <span className="text-xs text-slate-400">
                {transactions.length} transactions recorded
              </span>
            </div>

            <div className="overflow-x-auto flex-1">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-3 font-medium">Idempotency Key</th>
                    <th className="pb-3 font-medium">Source</th>
                    <th className="pb-3 font-medium">FX Rate</th>
                    <th className="pb-3 font-medium">Settled Amount</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-slate-800/20">
                      <td className="py-3 text-slate-300 font-semibold truncate max-w-[140px]" title={tx.idempotency_key}>
                        {tx.idempotency_key}
                      </td>
                      <td className="py-3 text-slate-300">
                        {tx.source_amount} {tx.source_currency}
                      </td>
                      <td className="py-3 text-slate-400">{tx.fx_rate_applied}</td>
                      <td className="py-3 text-white font-bold">
                        {tx.settled_amount} {tx.settled_currency}
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide ${
                            tx.status === "SETTLED"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          }`}
                        >
                          {tx.status}
                        </span>
                      </td>
                      <td className="py-3 text-slate-400">{tx.latency_ms}ms</td>
                    </tr>
                  ))}
                  {transactions.length === 0 && (
                    <tr>
                      <td colSpan={6} className="text-center py-10 text-slate-500">
                        No transactions recorded yet. Run a settlement simulation!
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
