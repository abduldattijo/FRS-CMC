#!/usr/bin/env python3
"""
Quick test to verify all routes are working
"""

import sys

print("Testing route imports...")

try:
    from app.main import app
    print("✅ App imported successfully")

    # List all routes
    print("\nRegistered routes:")
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'N/A'
            print(f"  {methods:8} {route.path}")

    print("\n✅ All routes loaded successfully!")
    print("\nYou should see routes like:")
    print("  - POST /api/v1/video/process")
    print("  - GET  /api/v1/detections/stats")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
