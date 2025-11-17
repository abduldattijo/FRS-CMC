#!/usr/bin/env python3
"""
Test script to diagnose the 500 error when saving detections
"""

import sys
from datetime import datetime
from sqlalchemy.orm import Session

# Test database operations
try:
    print("Testing detection save...")

    from app.models.enhanced_database import Detection, UnknownPerson, SessionLocal

    # Get database session
    db = SessionLocal()

    # Try to query detections
    detections = db.query(Detection).all()
    print(f"✅ Found {len(detections)} existing detections in database")

    # Try to query unknown persons
    unknowns = db.query(UnknownPerson).all()
    print(f"✅ Found {len(unknowns)} unknown persons in database")

    # Test creating a detection
    test_detection = Detection(
        person_id=None,
        unknown_person_id=unknowns[0].id if len(unknowns) > 0 else None,
        video_name="test_video.mp4",
        video_path="/tmp/test.mp4",
        frame_number=1,
        timestamp=datetime.now(),
        confidence=0.9,
        face_location_top=100,
        face_location_right=200,
        face_location_bottom=300,
        face_location_left=50,
        face_encoding=None,
        detection_image_path=None,
        detection_type="unknown_tracked",
    )

    db.add(test_detection)
    db.flush()  # Try to flush without committing

    print(f"✅ Test detection created with ID: {test_detection.id}")

    # Rollback the test
    db.rollback()
    print("✅ Test detection rolled back (not saved)")

    print("\n✅ Database operations are working correctly!")
    print("\nThe 500 error might be in response serialization.")
    print("Please share the full error traceback from your terminal.")

except Exception as e:
    print(f"\n❌ Error during test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()
