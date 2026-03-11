"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="Manus MVP Backend")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
