from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import router
from app.core.database import Base, engine
from app.core.metrics import PrometheusMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to safely create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="AntFlow Guard — Cross-Border Settlement & FX Anomaly Engine",
    description=(
        "Production-grade distributed cross-border payment settlement microservice featuring "
        "idempotent ledger mutations, optimistic/pessimistic locking, and real-time interbank FX risk triage."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend operator dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable Prometheus telemetry middleware
app.add_middleware(PrometheusMiddleware)

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "service": "AntFlow Guard",
        "status": "healthy",
        "version": "1.0.0",
    }


@app.get(
    "/metrics",
    tags=["Observability"],
    summary="Prometheus Metrics Endpoint",
    description="Exposes RED metrics and settlement business telemetry in standard Prometheus format.",
)
def get_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
