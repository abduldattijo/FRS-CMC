"""
System tests to verify installation and basic functionality
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all required packages can be imported"""
    print("Testing package imports...")

    try:
        import fastapi
        print("  ✓ FastAPI")
    except ImportError as e:
        print(f"  ✗ FastAPI: {e}")
        return False

    try:
        import cv2
        print("  ✓ OpenCV")
    except ImportError as e:
        print(f"  ✗ OpenCV: {e}")
        return False

    try:
        import face_recognition
        print("  ✓ face_recognition")
    except ImportError as e:
        print(f"  ✗ face_recognition: {e}")
        return False

    try:
        import sqlalchemy
        print("  ✓ SQLAlchemy")
    except ImportError as e:
        print(f"  ✗ SQLAlchemy: {e}")
        return False

    try:
        import numpy
        print("  ✓ NumPy")
    except ImportError as e:
        print(f"  ✗ NumPy: {e}")
        return False

    try:
        import PIL
        print("  ✓ Pillow")
    except ImportError as e:
        print(f"  ✗ Pillow: {e}")
        return False

    return True


def test_directories():
    """Test that required directories exist"""
    print("\nTesting directory structure...")

    required_dirs = [
        "app",
        "app/api",
        "app/core",
        "app/models",
        "data/uploads",
        "data/known_faces",
        "data/detections",
        "data/database",
        "frontend/static",
        "frontend/templates",
    ]

    all_exist = True
    for dir_path in required_dirs:
        exists = os.path.isdir(dir_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")
        if not exists:
            all_exist = False

    return all_exist


def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")

    try:
        from app.core.config import settings
        print(f"  ✓ Configuration loaded")
        print(f"    - App Name: {settings.APP_NAME}")
        print(f"    - Version: {settings.VERSION}")
        print(f"    - Environment: {settings.ENVIRONMENT}")
        return True
    except Exception as e:
        print(f"  ✗ Configuration error: {e}")
        return False


def test_database():
    """Test database initialization"""
    print("\nTesting database...")

    try:
        from app.models.database import init_db, engine

        # Initialize database
        init_db()
        print("  ✓ Database initialized")

        # Test connection
        with engine.connect() as conn:
            print("  ✓ Database connection successful")

        return True
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return False


def test_face_detection():
    """Test basic face detection functionality"""
    print("\nTesting face detection...")

    try:
        from app.core.face_detector import FaceDetector
        import numpy as np

        detector = FaceDetector()
        print("  ✓ FaceDetector initialized")

        # Create a dummy image
        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        print("  ✓ Test image created")

        # This won't find faces but tests the function works
        faces = detector.detect_faces(dummy_image)
        print(f"  ✓ Face detection function works (found {len(faces)} faces)")

        return True
    except Exception as e:
        print(f"  ✗ Face detection error: {e}")
        return False


def run_all_tests():
    """Run all system tests"""
    print("=" * 60)
    print("  Facial Recognition System - Installation Tests")
    print("=" * 60)

    tests = [
        ("Package Imports", test_imports),
        ("Directory Structure", test_directories),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Face Detection", test_face_detection),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\nUnexpected error in {name}: {e}")
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("  Test Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)

    if all_passed:
        print("  All tests passed! System is ready to use.")
        print("  Run 'python run.py' to start the server.")
    else:
        print("  Some tests failed. Please check the errors above.")
        print("  Refer to README.md for troubleshooting.")

    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
