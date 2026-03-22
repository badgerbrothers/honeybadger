"""RAG Service entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import rag, rag_collections
from app.services.queue_service import queue_service

app = FastAPI(title="Badgers RAG Service")


@app.on_event("startup")
async def startup_event():
    """Initialize database and queue dependencies."""
    import app.models  # noqa: F401

    await init_db()
    await queue_service.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Release external clients."""
    await queue_service.close()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rag.router)
app.include_router(rag_collections.router)


@app.get("/api/rag")
async def rag_root():
    return {"status": "ok", "service": "rag-service"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "rag-service"}
