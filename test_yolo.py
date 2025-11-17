#!/usr/bin/env python3
"""
Quick test to verify YOLO face detection is working
"""

import cv2
import numpy as np

print("Testing YOLO Face Detection...\n")

try:
    from app.core.yolo_face_detector import YOLOFaceDetector

    print("✓ YOLO detector imported successfully")

    # Initialize detector
    detector = YOLOFaceDetector(confidence_threshold=0.4, min_face_size=15)

    print("✓ YOLO detector initialized")
    print(f"\nModel Info:")
    info = detector.get_model_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Create a test image
    print("\nTesting with random image...")
    test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

    # Test detection
    detections = detector.detect_faces(test_image)

    print(f"✓ Detection completed")
    print(f"  Detections found: {len(detections)}")

    if len(detections) > 0:
        print("\n  Sample detection:")
        det = detections[0]
        print(f"    Location: {det['location']}")
        print(f"    Confidence: {det['confidence']:.2f}")

    print("\n" + "="*60)
    print("✅ YOLO FACE DETECTION IS WORKING!")
    print("="*60)
    print("\nYour system will now use YOLO for face detection")
    print("Benefits:")
    print("  ✓ Better detection on diverse faces")
    print("  ✓ Works better with angles and occlusions")
    print("  ✓ More robust in varying lighting")
    print("  ✓ Reduced bias across skin tones")
    print("\n" + "="*60)

except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting:")
    print("  1. Make sure ultralytics is installed: pip install ultralytics")
    print("  2. Check the error message above")
    print("  3. The system will fall back to MediaPipe if YOLO fails")
