#!/usr/bin/env bash
# AntFlow Guard — One-Click Developer Environment Startup
# Starts backend, frontend, and opens browser dashboards automatically.

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================================"
echo "  🚀 Starting AntFlow Guard Full-Stack Platform"
echo "========================================================"

# 1. Start Backend API in background
echo "[1/3] Starting FastAPI Backend on port 8000..."
source .venv/bin/activate
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > .backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend.pid
echo "      Backend running (PID: $BACKEND_PID) -> http://localhost:8000"

# 2. Start Frontend Next.js in background (if npm dependencies exist)
if [ -d "frontend" ]; then
    echo "[2/3] Starting Next.js Frontend Operator Console on port 3000..."
    cd frontend
    nohup npm run dev > ../.frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > ../.frontend.pid
    cd "$PROJECT_DIR"
    echo "      Frontend running (PID: $FRONTEND_PID) -> http://localhost:3000"
fi

# 3. Wait 2 seconds for services to initialize
sleep 2

# 4. Automatically open browser tabs on Mac
echo "[3/3] Opening application tabs in default browser..."
open "http://localhost:3000" 2>/dev/null || true
open "http://localhost:8000/docs" 2>/dev/null || true

echo "========================================================"
echo "  ✅ AntFlow Guard is UP and RUNNING!"
echo "     - Frontend Console   : http://localhost:3000"
echo "     - Backend API Docs   : http://localhost:8000/docs"
echo "     - API Healthcheck    : http://localhost:8000/health"
echo "     - Metrics Stream     : http://localhost:8000/metrics"
echo "     - Prometheus Engine  : http://localhost:9090"
echo "     - Grafana SRE Portal : http://localhost:3001 (admin / admin)"
echo ""
echo "  To stop everything, simply run: bash stop.sh"
echo "========================================================"
