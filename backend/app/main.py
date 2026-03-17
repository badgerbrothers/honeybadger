"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import projects, conversations, tasks, rag, runs, artifacts, memory
from app.services.queue_service import queue_service

app = FastAPI(title="Badgers MVP Backend")


@app.on_event("startup")
async def startup_event():
    """Initialize external service clients."""
    await queue_service.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Release external service clients."""
    await queue_service.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(conversations.router)
app.include_router(tasks.router)
app.include_router(rag.router)
app.include_router(runs.router)
app.include_router(artifacts.router)
app.include_router(memory.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
