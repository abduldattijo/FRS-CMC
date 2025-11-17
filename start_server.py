#!/usr/bin/env python3
"""
Simple server startup script (no auto-reload)
Use this if run.py has issues with the reloader
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print(f"  {settings.APP_NAME} v{settings.VERSION}")
    print("=" * 60)
    print(f"\n  Server: http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("\n" + "=" * 60)
    print("\nStarting server (no auto-reload)...\n")

    # Run without reload for stability
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Disabled for stability
        log_level="info"
    )
