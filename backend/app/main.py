"""FastAPI application entry point."""
from fastapi import FastAPI

app = FastAPI(title="Badgers MVP Backend")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
