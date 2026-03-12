"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import projects, conversations, tasks, rag

app = FastAPI(title="Badgers MVP Backend")

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}
