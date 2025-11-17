"""
FastAPI application for Cross-Video Identity Linking System
Intelligence/surveillance application for tracking persons across multiple CCTV videos
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

# Import API routes
from .api.routes import cross_video
from .models.cross_video_database import init_db

# Initialize FastAPI app
app = FastAPI(
    title="Cross-Video Identity Linking System",
    description="Intelligence platform for tracking individuals across multiple CCTV videos",
    version="1.0.0",
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

# Setup templates
templates = Jinja2Templates(directory="frontend/templates")


@app.get("/")
async def root(request: Request):
    """Home page - Cross-video analysis dashboard"""
    return templates.TemplateResponse("cross_video_dashboard.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "cross-video-identity-linking"}


# Include API routers (must be before static mounts to avoid route conflicts)
app.include_router(cross_video.router)


@app.on_event("startup")
async def startup_event():
    """Initialize cross-video database on startup"""
    init_db()


# Mount static files LAST to avoid intercepting API routes
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Serve data directory (for images, videos, etc.)
if os.path.exists("data"):
    app.mount("/data", StaticFiles(directory="data"), name="data")


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  Cross-Video Identity Linking System")
    print("  Intelligence Platform for Multi-Video Surveillance")
    print("=" * 60)
    print("\n  Dashboard: http://localhost:8001")
    print("  API Docs: http://localhost:8001/docs")
    print("\n" + "=" * 60)
    print("\nStarting server...\n")

    uvicorn.run(
        "app.main_cross_video:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
