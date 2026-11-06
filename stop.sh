#!/usr/bin/env bash
# AntFlow Guard — Graceful Shutdown Script
# Terminates background backend and frontend processes.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================================"
echo "  🛑 Stopping AntFlow Guard Services"
echo "========================================================"

if [ -f ".backend.pid" ]; then
    PID=$(cat .backend.pid)
    echo "Stopping Backend API (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    rm -f .backend.pid
fi

if [ -f ".frontend.pid" ]; then
    PID=$(cat .frontend.pid)
    echo "Stopping Frontend Next.js (PID: $PID)..."
    kill "$PID" 2>/dev/null || true
    rm -f .frontend.pid
fi

# Fallback cleanup for any stray uvicorn processes on port 8000
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# If Docker compose is running, shut down gracefully
if command -v docker &> /dev/null; then
    docker compose down 2>/dev/null || true
fi

echo "✅ All AntFlow Guard services stopped cleanly."
echo "========================================================"
