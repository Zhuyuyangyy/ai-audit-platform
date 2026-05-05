# Main FastAPI Application
# AI Compliance Audit Platform

import sys
import os

# Add backend path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from app.core.database import init_db
from app.api.routes import router

# Initialize database on startup
init_db()

app = FastAPI(
    title="政企大模型应用安全合规审计与输出风险控制系统",
    version="1.0.0",
    description="政务大模型AI合规审计与熔断控制平台",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    return {
        "service": "AI Compliance Audit Platform",
        "version": "1.0",
        "description": "政务大模型应用安全合规审计与输出风险控制系统",
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "audit_prompt": "/api/v1/audit_prompt",
            "audit_output": "/api/v1/audit_output",
            "audit_interaction": "/api/v1/audit_interaction"
        }
    }

@app.get("/frontend")
async def frontend():
    """Serve the Vue3 frontend"""
    index_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not found. Please ensure frontend/index.html exists."}

# Startup event
@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("  政企大模型应用安全合规审计与输出风险控制系统 V1.0")
    print("  AI Compliance Audit Platform v1.0")
    print("=" * 60)
    print("  API Docs: http://localhost:8014/docs")
    print("  Health:   http://localhost:8014/api/v1/health")
    print("  Frontend: http://localhost:8014/frontend")
    print("=" * 60)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8014, reload=False)