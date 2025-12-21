from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import os
from datetime import datetime

from .routers import convert, user, auth, counsellor, counsellee, upload, capture, notifications, templates
from .database import engine
from sqlalchemy import text
# from . import models

# models.Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = ["*"]
# origins = [
#     "https://ymr-counselling.vercel.app/",
#     "https://www.ymrcounselling.com",
#     "https://ymrcounselling.com",
#     "http://localhost:8080",
#     "http://localhost:8080/"
#     "https://*.lovableproject.com"
#     "https://*.lovable.app"
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(convert.router)
api_router.include_router(counsellor.router)
api_router.include_router(counsellee.router)
api_router.include_router(upload.router)
api_router.include_router(capture.router)
api_router.include_router(notifications.router)
api_router.include_router(templates.router)


app.include_router(api_router)

@app.get("/")
def read_root():
    return {"Hello": "World - YMR IS HERE - THE FLOODGATES ARE OPEN!!!"}


# Health Check Endpoints for Kubernetes
@app.get("/health")
def health_check():
    """
    Basic health check endpoint for Kubernetes liveness and readiness probes.
    Returns 200 OK if the application is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-data-capture-portal",
        "version": "1.0.1"
    }


@app.get("/health/live")
def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if the application process is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - start_time
    }


@app.get("/health/ready")
def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    Returns 200 if the application is ready to serve traffic.
    Checks database connectivity and other dependencies.
    """
    checks = {
        "application": "ok",
        "database": "unknown",
        "dependencies": "ok"
    }
    
    try:
        # Test database connectivity
        with engine.connect() as connection:
            # Execute a simple query to test database connectivity
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            checks["database"] = "ok"
        
        # All checks passed
        health_status = {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
        
        return health_status
        
    except Exception as e:
        # Database or other dependency failed
        checks["database"] = f"failed: {str(e)}"
        
        # Return 503 Service Unavailable if not ready
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks,
                "error": str(e)
            }
        )


@app.get("/health/startup")
def startup_check():
    """
    Kubernetes startup probe endpoint.
    Returns 200 when the application has completed startup.
    """
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "startup_time": datetime.fromtimestamp(start_time).isoformat()
    }


@app.get("/health/status")
def detailed_health_status():
    """
    Comprehensive health status endpoint.
    Returns detailed information about application health and dependencies.
    """
    uptime = time.time() - start_time
    
    # Database check
    db_status = "unknown"
    db_error = None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            db_version = result.fetchone()[0]
            db_status = "connected"
    except Exception as e:
        db_status = "failed"
        db_error = str(e)
        db_version = None
    
    return {
        "service": "ai-data-capture-portal",
        "version": "1.0.0",
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": {
            "seconds": uptime,
            "human_readable": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        },
        "startup_time": datetime.fromtimestamp(start_time).isoformat(),
        "environment": {
            "python_version": os.sys.version,
            "environment": os.getenv("ENVIRONMENT", "development")
        },
        "dependencies": {
            "database": {
                "status": db_status,
                "version": db_version,
                "error": db_error
            }
        },
        "endpoints": {
            "health": "/health",
            "liveness": "/health/live",
            "readiness": "/health/ready",
            "startup": "/health/startup",
            "detailed": "/health/status"
        }
    }


# Store application start time
start_time = time.time()