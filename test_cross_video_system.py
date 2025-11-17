#!/usr/bin/env python3
"""
Test script for Cross-Video Identity Linking System
Verifies all components are working correctly
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        from app.models.cross_video_database import (
            Video, VideoFace, RawDetection, PersonCluster, CrossVideoMatch, AnalysisJob
        )
        print("  ✓ Database models")

        from app.core.face_clustering import FaceClusterer
        print("  ✓ Face clustering module")

        from app.core.cross_video_matcher import CrossVideoMatcher
        print("  ✓ Cross-video matcher module")

        from app.core.cross_video_processor import CrossVideoProcessor
        print("  ✓ Cross-video processor module")

        from app.api.routes import cross_video
        print("  ✓ API routes")

        from app.main_cross_video import app
        print("  ✓ FastAPI application")

        return True

    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_database():
    """Test database initialization"""
    print("\nTesting database...")

    try:
        from app.models.cross_video_database import SessionLocal, Base, engine

        # Check if tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            'videos',
            'video_faces',
            'raw_detections',
            'person_clusters',
            'cross_video_matches',
            'analysis_jobs',
            'cluster_faces'
        ]

        missing_tables = set(expected_tables) - set(tables)

        if missing_tables:
            print(f"  ✗ Missing tables: {missing_tables}")
            return False

        print(f"  ✓ All {len(expected_tables)} tables exist")
        return True

    except Exception as e:
        print(f"  ✗ Database test failed: {e}")
        return False


def test_face_clustering():
    """Test face clustering functionality"""
    print("\nTesting face clustering...")

    try:
        from app.core.face_clustering import FaceClusterer
        import numpy as np

        clusterer = FaceClusterer(similarity_threshold=0.85)

        # Create dummy face encodings (5 faces, 128D vectors)
        # 2 similar faces, 3 different faces
        encodings = [
            np.random.rand(128),  # Face 1
            np.random.rand(128),  # Face 2
            np.random.rand(128),  # Face 3
            np.random.rand(128),  # Face 4
            np.random.rand(128),  # Face 5
        ]

        # Make face 1 and 2 very similar
        encodings[1] = encodings[0] + np.random.rand(128) * 0.01

        # Test clustering
        labels, num_clusters = clusterer.cluster_faces(encodings, min_samples=1)

        print(f"  ✓ Clustered {len(encodings)} faces into {num_clusters} groups")

        # Test similarity computation
        similarity = clusterer.compute_similarity(encodings[0], encodings[1])
        print(f"  ✓ Similarity computation works (similar faces: {similarity:.3f})")

        return True

    except Exception as e:
        print(f"  ✗ Face clustering test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cross_video_matcher():
    """Test cross-video matcher initialization"""
    print("\nTesting cross-video matcher...")

    try:
        from app.core.cross_video_matcher import CrossVideoMatcher
        import numpy as np

        matcher = CrossVideoMatcher(
            similarity_threshold=0.85,
            clustering_threshold=0.90
        )

        # Test similarity computation
        enc1 = np.random.rand(128)
        enc2 = np.random.rand(128)

        similarity = matcher.compute_similarity(enc1, enc2)
        print(f"  ✓ Matcher initialized and similarity computation works ({similarity:.3f})")

        return True

    except Exception as e:
        print(f"  ✗ Cross-video matcher test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_video_processor():
    """Test video processor initialization"""
    print("\nTesting video processor...")

    try:
        from app.core.cross_video_processor import CrossVideoProcessor

        processor = CrossVideoProcessor()
        print(f"  ✓ Video processor initialized")
        print(f"  ✓ Face detector: {processor.face_detector.__class__.__name__}")
        print(f"  ✓ Face clusterer: {processor.face_clusterer.__class__.__name__}")

        return True

    except Exception as e:
        print(f"  ✗ Video processor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_app():
    """Test FastAPI application"""
    print("\nTesting FastAPI application...")

    try:
        from app.main_cross_video import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"  ✓ Health endpoint works")

        # Test videos endpoint
        response = client.get("/api/v1/cross-video/videos")
        assert response.status_code == 200
        print(f"  ✓ Videos endpoint works")

        # Test clusters endpoint
        response = client.get("/api/v1/cross-video/clusters")
        assert response.status_code == 200
        print(f"  ✓ Clusters endpoint works")

        return True

    except Exception as e:
        print(f"  ✗ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Cross-Video Identity Linking System - Test Suite")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Face Clustering", test_face_clustering),
        ("Cross-Video Matcher", test_cross_video_matcher),
        ("Video Processor", test_video_processor),
        ("FastAPI Application", test_api_app),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nTo start the server, run:")
        print("  python start_cross_video.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
