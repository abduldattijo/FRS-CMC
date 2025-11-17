#!/usr/bin/env python3
"""
Start the ENHANCED facial recognition system with cross-video tracking
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print(f"  {settings.APP_NAME} v{settings.VERSION} - ENHANCED MODE")
    print("=" * 70)
    print(f"\n  Server: http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("\n  ENHANCED FEATURES:")
    print("  ✓ Cross-video face tracking")
    print("  ✓ Unknown person clustering")
    print("  ✓ Automatic face database building")
    print("  ✓ Unknown person promotion")
    print("\n" + "=" * 70)
    print("\nStarting enhanced server...\n")

    uvicorn.run(
        "app.main_enhanced:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
