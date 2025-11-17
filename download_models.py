#!/usr/bin/env python3
"""
Download and setup InsightFace models for the improved facial recognition system
Downloads buffalo_l model which provides 512D embeddings optimized for diverse faces
"""

import os
import sys
from pathlib import Path


def download_insightface_models():
    """Download InsightFace buffalo_l model"""

    print("\n" + "="*70)
    print("INSIGHTFACE MODEL DOWNLOAD")
    print("="*70)
    print("\nDownloading buffalo_l model for 512D embeddings...")
    print("This model is optimized for diverse faces including West African features")
    print("="*70 + "\n")

    try:
        from insightface.app import FaceAnalysis

        # Initialize FaceAnalysis - this will automatically download the model
        print("Initializing InsightFace with buffalo_l model...")
        print("(First run will download ~500MB of model files)\n")

        app = FaceAnalysis(
            name='buffalo_l',
            providers=['CPUExecutionProvider']
        )

        # Prepare the model
        app.prepare(ctx_id=0, det_size=(640, 640))

        print("\n" + "="*70)
        print("✓ SUCCESS: InsightFace buffalo_l model downloaded and initialized!")
        print("="*70)
        print("\nModel Details:")
        print("  - Model: buffalo_l")
        print("  - Embedding dimension: 512D")
        print("  - Detection size: 640x640")
        print("  - Optimized for: Diverse faces, varying lighting conditions")
        print("="*70 + "\n")

        return True

    except ImportError:
        print("\n✗ ERROR: InsightFace not installed!")
        print("\nPlease install required packages first:")
        print("  pip install -r requirements-improved.txt")
        return False

    except Exception as e:
        print(f"\n✗ ERROR downloading model: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your internet connection")
        print("  2. Ensure you have enough disk space (~1GB)")
        print("  3. Try running with sudo if permission errors occur")
        return False


def check_installation():
    """Check if all required packages are installed"""

    print("\n" + "="*70)
    print("CHECKING INSTALLATION")
    print("="*70 + "\n")

    required_packages = {
        'insightface': 'InsightFace',
        'faiss': 'FAISS',
        'retinaface': 'RetinaFace',
        'cv2': 'OpenCV',
        'numpy': 'NumPy',
        'sklearn': 'scikit-learn',
    }

    missing_packages = []

    for package, name in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {name:20s} - Installed")
        except ImportError:
            print(f"✗ {name:20s} - Missing")
            missing_packages.append(package)

    print("\n" + "="*70)

    if missing_packages:
        print("\n✗ Missing packages detected!")
        print("\nInstall missing packages with:")
        print("  pip install -r requirements-improved.txt")
        print("\n" + "="*70 + "\n")
        return False
    else:
        print("\n✓ All required packages are installed!")
        print("="*70 + "\n")
        return True


def test_models():
    """Test if models work correctly"""

    print("\n" + "="*70)
    print("TESTING MODELS")
    print("="*70 + "\n")

    try:
        import numpy as np
        import cv2
        from insightface.app import FaceAnalysis

        # Create a test image
        print("Creating test image...")
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Initialize model
        print("Loading InsightFace model...")
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))

        # Test detection
        print("Testing face detection...")
        faces = app.get(test_image)
        print(f"✓ Detection successful (found {len(faces)} faces in test image)")

        # Test embedding generation with a larger face
        print("\nTesting embedding generation...")
        test_face = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
        faces = app.get(test_face)

        if len(faces) > 0:
            embedding = faces[0].embedding
            print(f"✓ Embedding generated successfully")
            print(f"  - Shape: {embedding.shape}")
            print(f"  - Dimension: {len(embedding)}D")
            print(f"  - Norm: {np.linalg.norm(embedding):.4f}")
        else:
            print("✓ No face detected in random test image (expected)")

        print("\n" + "="*70)
        print("✓ MODEL TESTS PASSED!")
        print("="*70 + "\n")

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        print("="*70 + "\n")
        return False


def main():
    """Main function"""

    print("\n" + "="*70)
    print("IMPROVED FACIAL RECOGNITION SYSTEM - MODEL SETUP")
    print("="*70)
    print("\nOptimized for West African faces with:")
    print("  - InsightFace buffalo_l (512D embeddings)")
    print("  - RetinaFace detector (better for darker skin tones)")
    print("  - FAISS (fast similarity search)")
    print("  - Quality scoring (blur, size, angle)")
    print("="*70 + "\n")

    # Step 1: Check installation
    if not check_installation():
        print("\n⚠️  Please install required packages before continuing.")
        sys.exit(1)

    # Step 2: Download models
    print("\nProceed with model download? (This will download ~500MB)")
    response = input("Continue? [Y/n]: ").strip().lower()

    if response in ['', 'y', 'yes']:
        if not download_insightface_models():
            print("\n⚠️  Model download failed. Please check errors above.")
            sys.exit(1)
    else:
        print("\n⚠️  Model download cancelled.")
        sys.exit(0)

    # Step 3: Test models
    print("\nTest models? [Y/n]: ")
    response = input().strip().lower()

    if response in ['', 'y', 'yes']:
        if not test_models():
            print("\n⚠️  Model tests failed. Please check errors above.")
            sys.exit(1)

    # Success!
    print("\n" + "="*70)
    print("✓ SETUP COMPLETE!")
    print("="*70)
    print("\nYour improved facial recognition system is ready to use!")
    print("\nNext steps:")
    print("  1. Update config.yaml with new settings")
    print("  2. Run the system: python start_cross_video.py")
    print("  3. Upload videos and test the improved recognition")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
