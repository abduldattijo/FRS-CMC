"""
Enhanced main FastAPI application with cross-video face tracking
Use this instead of main.py for the enhanced tracking features
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

from .core.config import settings
from .models.enhanced_database import init_db
from .api.routes import persons  # Keep the original persons route
from .api.routes import enhanced_video  # Use enhanced video route

# Initialize FastAPI app
app = FastAPI(
    title=f"{settings.APP_NAME} - Enhanced",
    version=settings.VERSION,
    description="Facial Recognition System with Cross-Video Face Tracking",
    debug=settings.DEBUG,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent / "frontend" / "static"
templates_path = Path(__file__).parent.parent / "frontend" / "templates"

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
templates = Jinja2Templates(directory=str(templates_path))

# Include API routers
app.include_router(persons.router, prefix="/api/v1")
app.include_router(enhanced_video.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize enhanced database on startup"""
    print("Initializing ENHANCED database with cross-video tracking...")
    init_db()
    print("Enhanced database initialized successfully!")
    print(f"Starting {settings.APP_NAME} v{settings.VERSION} - ENHANCED MODE")
    print(f"Environment: {settings.ENVIRONMENT}")
    print("\nFeatures enabled:")
    print("  ✓ Registered person recognition")
    print("  ✓ Cross-video unknown person tracking")
    print("  ✓ Automatic unknown person clustering")
    print("  ✓ Unknown person promotion to registered")


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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": f"{settings.APP_NAME} - Enhanced",
        "version": settings.VERSION,
        "features": ["cross_video_tracking", "unknown_person_clustering"]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main_enhanced:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
