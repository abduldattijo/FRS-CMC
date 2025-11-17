#!/usr/bin/env python3
"""
Startup script for Cross-Video Identity Linking System
Intelligence platform for tracking persons across multiple CCTV videos
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("  CROSS-VIDEO IDENTITY LINKING SYSTEM")
    print("  Intelligence Platform for Multi-Video Surveillance Analysis")
    print("=" * 80)
    print("\n  📊 Dashboard: http://localhost:8001")
    print("  📚 API Docs: http://localhost:8001/docs")
    print("  📖 ReDoc: http://localhost:8001/redoc")
    print("\n" + "=" * 80)
    print("\n🎯 System Capabilities:")
    print("  • Upload and process multiple CCTV videos")
    print("  • Detect and de-duplicate faces within each video")
    print("  • Match faces ACROSS different videos (NOT within same video)")
    print("  • Build person clusters showing: 'Person X in videos A, C, E'")
    print("  • Network visualization of cross-video appearances")
    print("\n" + "=" * 80)
    print("\nStarting server...\n")

    uvicorn.run(
        "app.main_cross_video:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
