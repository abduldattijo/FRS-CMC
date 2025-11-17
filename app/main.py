"""
Main FastAPI application for the Facial Recognition System
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

from .core.config import settings
from .models.enhanced_database import init_db  # Use enhanced database
from .api.routes import persons, video, recognition
from .api.routes import enhanced_video  # Add enhanced video route

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Facial Recognition System for CCTV Video Analysis",
    debug=settings.DEBUG,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent / "frontend" / "static"
templates_path = Path(__file__).parent.parent / "frontend" / "templates"
detections_path = Path(__file__).parent.parent / "data" / "detections"
known_faces_path = Path(__file__).parent.parent / "data" / "known_faces"

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount detections directory to serve detection images
if detections_path.exists():
    app.mount("/detections", StaticFiles(directory=str(detections_path)), name="detections")

# Mount known_faces directory to serve registered person images
if known_faces_path.exists():
    app.mount("/known_faces", StaticFiles(directory=str(known_faces_path)), name="known_faces")

templates = Jinja2Templates(directory=str(templates_path))

# Include API routers
app.include_router(persons.router, prefix="/api/v1")
app.include_router(video.router, prefix="/api/v1")
app.include_router(recognition.router, prefix="/api/v1")
app.include_router(enhanced_video.router, prefix="/api/v1")  # Enhanced video with cross-video tracking


@app.on_event("startup")
async def startup_event():
    """Initialize enhanced database on startup"""
    print("Initializing ENHANCED database...")
    init_db()
    print("Enhanced database initialized successfully!")
    print(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print("\nAvailable endpoints:")
    print("  - Basic video: POST /api/v1/video/process")
    print("  - Enhanced video (cross-tracking): POST /api/v1/enhanced-video/process")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Person registration page"""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/monitor", response_class=HTMLResponse)
async def monitor_page(request: Request):
    """Detection monitoring page"""
    return templates.TemplateResponse("monitor.html", {"request": request})


@app.get("/unknowns", response_class=HTMLResponse)
async def unknowns_page(request: Request):
    """Unknown persons gallery page"""
    return templates.TemplateResponse("unknowns.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
