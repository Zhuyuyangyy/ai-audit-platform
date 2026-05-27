"""FastAPI application entry point"""
from fastapi import FastAPI
app = FastAPI(title="ai-audit-platform")
@app.get("/health")
async def health(): return {"status": "ok"}
