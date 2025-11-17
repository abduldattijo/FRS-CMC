#!/usr/bin/env python3
"""
Startup script for the Facial Recognition System
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    print("=" * 60)
    print(f"  {settings.APP_NAME} v{settings.VERSION}")
    print("=" * 60)
    print(f"\n  Environment: {settings.ENVIRONMENT}")
    print(f"  Server: http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("\n" + "=" * 60)
    print("\nStarting server...\n")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
