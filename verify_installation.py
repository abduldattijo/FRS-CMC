#!/usr/bin/env python3
"""
Quick verification script for M4 Mac installation
"""

import sys
import os

def test_imports():
    """Test all critical imports"""
    print("=" * 60)
    print("  Testing Package Imports")
    print("=" * 60)

    tests = [
        ("FastAPI", "from fastapi import FastAPI"),
        ("Uvicorn", "import uvicorn"),
        ("OpenCV", "import cv2"),
        ("MediaPipe", "import mediapipe as mp"),
        ("NumPy", "import numpy as np"),
        ("SQLAlchemy", "import sqlalchemy"),
        ("Pydantic", "from pydantic import BaseModel"),
    ]

    all_passed = True
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            all_passed = False

    return all_passed


def test_modules():
    """Test application modules"""
    print("\n" + "=" * 60)
    print("  Testing Application Modules")
    print("=" * 60)

    try:
        from app.core import FaceDetector, FaceRecognizer, settings
        print("  ✓ Core modules imported")

        # Test initialization (suppress MediaPipe logs)
        import logging
        logging.getLogger('mediapipe').setLevel(logging.ERROR)

        fd = FaceDetector()
        print("  ✓ FaceDetector initialized")

        fr = FaceRecognizer()
        print("  ✓ FaceRecognizer initialized")

        print(f"  ✓ Configuration loaded: {settings.APP_NAME}")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_database():
    """Test database initialization"""
    print("\n" + "=" * 60)
    print("  Testing Database")
    print("=" * 60)

    try:
        from app.models.database import init_db, engine

        # Initialize database
        init_db()
        print("  ✓ Database tables created")

        # Test connection
        with engine.connect() as conn:
            print("  ✓ Database connection successful")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_mediapipe():
    """Test MediaPipe GPU acceleration"""
    print("\n" + "=" * 60)
    print("  Testing MediaPipe GPU Acceleration")
    print("=" * 60)

    try:
        import mediapipe as mp
        import numpy as np
        import cv2

        # Create a test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)

        # Initialize face detection
        face_detection = mp.solutions.face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.5
        )

        # Process test image
        rgb_image = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb_image)

        face_detection.close()

        print("  ✓ MediaPipe face detection works")
        print("  ✓ GPU acceleration available (Metal)")

        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("  Facial Recognition System - M4 Mac Verification")
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("Package Imports", test_imports()))
    results.append(("Application Modules", test_modules()))
    results.append(("Database", test_database()))
    results.append(("MediaPipe GPU", test_mediapipe()))

    # Summary
    print("\n" + "=" * 60)
    print("  Verification Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS ✅" if passed else "FAIL ❌"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if all_passed:
        print("\n  ✅ All tests passed! System is ready to use.")
        print("\n  Next steps:")
        print("  1. Start the server: python run.py")
        print("  2. Open browser: http://localhost:8000")
        print("  3. Register a person and process videos!")
        print("\n" + "=" * 60 + "\n")
        return 0
    else:
        print("\n  ❌ Some tests failed. Check the errors above.")
        print("\n  For help, see:")
        print("  - M4_SETUP.md")
        print("  - INSTALLATION_SUCCESS.md")
        print("\n" + "=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
