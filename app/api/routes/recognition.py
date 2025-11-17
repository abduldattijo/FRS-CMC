"""
API routes for face recognition and detection queries
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Optional
from datetime import datetime, timedelta

from ...models.enhanced_database import Detection, Person, UnknownPerson
from ...schemas.recognition import DetectionListResponse, DetectionResponse, DetectionStats
from ..dependencies import get_db

router = APIRouter(prefix="/detections", tags=["Detections"])


@router.get("/", response_model=DetectionListResponse)
def get_detections(
    skip: int = 0,
    limit: int = 100,
    person_id: Optional[int] = Query(None, description="Filter by person ID"),
    video_name: Optional[str] = Query(None, description="Filter by video name"),
    unknown_only: bool = Query(False, description="Show only unknown faces"),
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter to this date"),
    db: Session = Depends(get_db),
):
    """
    Get list of all detections with optional filters

    Args:
        skip: Number of records to skip
        limit: Maximum number of records
        person_id: Filter by specific person
        video_name: Filter by video name
        unknown_only: Show only unknown faces
        start_date: Start date filter
        end_date: End date filter
        db: Database session

    Returns:
        List of detections
    """
    query = db.query(Detection)

    # Apply filters
    if person_id:
        query = query.filter(Detection.person_id == person_id)

    if video_name:
        query = query.filter(Detection.video_name == video_name)

    if unknown_only:
        # In enhanced schema, unknown faces have detection_type != "registered"
        query = query.filter(Detection.detection_type != "registered")

    if start_date:
        query = query.filter(Detection.timestamp >= start_date)

    if end_date:
        query = query.filter(Detection.timestamp <= end_date)

    # Order by most recent first
    query = query.order_by(Detection.timestamp.desc())

    total = query.count()
    detections = query.offset(skip).limit(limit).all()

    # Format response with person names (registered or unknown)
    detection_responses = []
    for detection in detections:
        person_name = None
        reference_image_path = None
        is_unknown = detection.detection_type != "registered"

        if detection.person_id:
            # Registered person
            person = db.query(Person).filter(Person.id == detection.person_id).first()
            if person:
                person_name = person.name
                reference_image_path = person.image_path  # Include registered person's image
        elif detection.unknown_person_id:
            # Unknown person
            unknown = db.query(UnknownPerson).filter(UnknownPerson.id == detection.unknown_person_id).first()
            if unknown:
                person_name = unknown.identifier
                reference_image_path = unknown.representative_image_path  # Include unknown's reference image

        detection_responses.append(
            {
                "id": detection.id,
                "person_id": detection.person_id,
                "person_name": person_name or "Unknown",
                "video_name": detection.video_name,
                "frame_number": detection.frame_number,
                "timestamp": detection.timestamp,
                "confidence": detection.confidence,
                "face_location": {
                    "top": detection.face_location_top,
                    "right": detection.face_location_right,
                    "bottom": detection.face_location_bottom,
                    "left": detection.face_location_left,
                }
                if detection.face_location_top is not None
                else None,
                "detection_image_path": detection.detection_image_path,
                "reference_image_path": reference_image_path,  # NEW: Reference image for comparison
                "is_unknown": is_unknown,
                "created_at": detection.created_at,
            }
        )

    return {"total": total, "detections": detection_responses}


@router.get("/stats", response_model=DetectionStats)
def get_detection_stats(
    start_date: Optional[datetime] = Query(None, description="Stats from this date"),
    end_date: Optional[datetime] = Query(None, description="Stats to this date"),
    db: Session = Depends(get_db),
):
    """
    Get statistics about detections

    Args:
        start_date: Start date for stats
        end_date: End date for stats
        db: Database session

    Returns:
        Detection statistics
    """
    query = db.query(Detection)

    if start_date:
        query = query.filter(Detection.timestamp >= start_date)

    if end_date:
        query = query.filter(Detection.timestamp <= end_date)

    # Total detections
    total_detections = query.count()

    # Known vs unknown (using enhanced schema)
    known_persons = query.filter(Detection.detection_type == "registered").count()
    unknown_persons = query.filter(Detection.detection_type != "registered").count()

    # Detections by person
    detections_by_person = {}
    person_stats = (
        db.query(Person.name, func.count(Detection.id))
        .join(Detection, Person.id == Detection.person_id)
        .group_by(Person.id, Person.name)
        .all()
    )

    for person_name, count in person_stats:
        detections_by_person[person_name] = count

    # Detections by date
    detections_by_date = {}
    date_stats = (
        db.query(func.date(Detection.timestamp), func.count(Detection.id))
        .group_by(func.date(Detection.timestamp))
        .order_by(func.date(Detection.timestamp))
        .all()
    )

    for date, count in date_stats:
        detections_by_date[str(date)] = count

    return {
        "total_detections": total_detections,
        "known_persons": known_persons,
        "unknown_persons": unknown_persons,
        "detections_by_person": detections_by_person,
        "detections_by_date": detections_by_date,
    }


@router.get("/{detection_id}", response_model=DetectionResponse)
def get_detection(detection_id: int, db: Session = Depends(get_db)):
    """
    Get a specific detection by ID

    Args:
        detection_id: Detection ID
        db: Database session

    Returns:
        Detection record
    """
    detection = db.query(Detection).filter(Detection.id == detection_id).first()

    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")

    person_name = None
    is_unknown = detection.detection_type != "registered"

    if detection.person_id:
        # Registered person
        person = db.query(Person).filter(Person.id == detection.person_id).first()
        if person:
            person_name = person.name
    elif detection.unknown_person_id:
        # Unknown person
        unknown = db.query(UnknownPerson).filter(UnknownPerson.id == detection.unknown_person_id).first()
        if unknown:
            person_name = unknown.identifier

    return {
        "id": detection.id,
        "person_id": detection.person_id,
        "person_name": person_name or "Unknown",
        "video_name": detection.video_name,
        "frame_number": detection.frame_number,
        "timestamp": detection.timestamp,
        "confidence": detection.confidence,
        "face_location": {
            "top": detection.face_location_top,
            "right": detection.face_location_right,
            "bottom": detection.face_location_bottom,
            "left": detection.face_location_left,
        }
        if detection.face_location_top is not None
        else None,
        "detection_image_path": detection.detection_image_path,
        "is_unknown": is_unknown,
        "created_at": detection.created_at,
    }


@router.get("/person/{person_id}/timeline")
def get_person_timeline(
    person_id: int,
    days: int = Query(7, description="Number of days to look back"),
    db: Session = Depends(get_db),
):
    """
    Get detection timeline for a specific person

    Args:
        person_id: Person ID
        days: Number of days to look back
        db: Database session

    Returns:
        Timeline of detections
    """
    person = db.query(Person).filter(Person.id == person_id).first()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    start_date = datetime.now() - timedelta(days=days)

    detections = (
        db.query(Detection)
        .filter(
            and_(Detection.person_id == person_id, Detection.timestamp >= start_date)
        )
        .order_by(Detection.timestamp.asc())
        .all()
    )

    timeline = []
    for detection in detections:
        timeline.append(
            {
                "timestamp": detection.timestamp,
                "video_name": detection.video_name,
                "frame_number": detection.frame_number,
                "confidence": detection.confidence,
                "detection_image_path": detection.detection_image_path,
            }
        )

    return {
        "person_id": person_id,
        "person_name": person.name,
        "timeline_days": days,
        "total_detections": len(timeline),
        "timeline": timeline,
    }
