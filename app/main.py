from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.database import Base, engine


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
        "Production-grade cross-border payment settlement microservice inspired by "
        "Ant International's TRX Global Development Centre architecture (Alipay+, Antom, WorldFirst)."
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

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "service": "AntFlow Guard",
        "status": "healthy",
        "version": "1.0.0",
    }
