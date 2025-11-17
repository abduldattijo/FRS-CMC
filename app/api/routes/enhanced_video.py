"""
Enhanced API routes for video processing with cross-video face tracking
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import shutil
import os
from datetime import datetime

from ...models.enhanced_database import Detection, UnknownPerson
from ...core.config import settings
from ...core.enhanced_video_processor import EnhancedVideoProcessor
from ...core.face_detector_mediapipe import FaceDetector
from ...core.enhanced_recognizer import EnhancedFaceRecognizer
from ..dependencies import get_db

router = APIRouter(prefix="/enhanced-video", tags=["Enhanced Video Processing"])


@router.post("/process")
async def process_video_with_tracking(
    video: UploadFile = File(...),
    frame_skip: Optional[int] = Form(None),
    save_frames: Optional[bool] = Form(True),
    confidence_threshold: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Process CCTV video with CROSS-VIDEO FACE TRACKING

    This endpoint:
    1. Matches faces against registered persons
    2. Matches faces against unknown persons from PREVIOUS videos
    3. Creates new unknown person entries for new faces
    4. Updates sighting counts for re-detected unknowns

    Returns detailed tracking information
    """
    # Validate video file
    file_ext = os.path.splitext(video.filename)[1].lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format. Supported: {settings.SUPPORTED_FORMATS}",
        )

    # Check file size
    video.file.seek(0, 2)
    file_size = video.file.tell()
    video.file.seek(0)

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save uploaded video
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_filename = f"{timestamp}_{video.filename}"
    video_path = os.path.join(settings.UPLOADS_DIR, video_filename)

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    try:
        # Initialize components
        face_detector = FaceDetector()
        face_recognizer = EnhancedFaceRecognizer()
        video_processor = EnhancedVideoProcessor(face_detector, face_recognizer)

        # Create output directory for detections
        output_dir = None
        if save_frames:
            output_dir = os.path.join(
                settings.DETECTIONS_DIR,
                f"{timestamp}_{os.path.splitext(video.filename)[0]}"
            )

        # Process the video with TRACKING
        result = video_processor.process_video_with_tracking(
            video_path=video_path,
            db=db,
            output_dir=output_dir,
            frame_skip=frame_skip,
            save_frames=save_frames,
            confidence_threshold=confidence_threshold,
        )

        # Save detections to database
        for detection_data in result["detections"]:
            # Serialize face encoding if available
            face_encoding_bytes = None
            if "encoding" in detection_data:
                import pickle
                face_encoding_bytes = pickle.dumps(detection_data["encoding"])

            detection = Detection(
                person_id=detection_data.get("person_id"),
                unknown_person_id=detection_data.get("unknown_person_id"),
                video_name=video_filename,
                video_path=video_path,
                frame_number=detection_data["frame_number"],
                timestamp=detection_data["timestamp"],
                confidence=detection_data.get("confidence", 0.0),
                face_location_top=detection_data["face_location"]["top"],
                face_location_right=detection_data["face_location"]["right"],
                face_location_bottom=detection_data["face_location"]["bottom"],
                face_location_left=detection_data["face_location"]["left"],
                face_encoding=face_encoding_bytes,
                detection_image_path=detection_data.get("detection_image_path"),
                detection_type=detection_data.get("detection_type", "unknown"),
            )
            db.add(detection)

        db.commit()

        # Format response
        response = {
            "video_name": video_filename,
            "total_frames": result["total_frames"],
            "processed_frames": result["processed_frames"],
            "total_detections": result["total_detections"],
            "breakdown": {
                "registered_persons": result["registered_detections"],
                "tracked_unknowns": result["tracked_unknown_detections"],
                "new_unknowns": result["new_unknown_detections"],
            },
            "new_unknowns_created": result["new_unknowns_created"],
            "processing_time_seconds": result["processing_time_seconds"],
            "message": f"Video processed successfully! Found {result['registered_detections']} registered persons, "
                      f"{result['tracked_unknown_detections']} previously seen unknowns, and "
                      f"{result['new_unknown_detections']} new unknown persons."
        }

        return response

    except Exception as e:
        # Clean up on error
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")


@router.get("/unknown-persons")
def list_unknown_persons(
    skip: int = 0,
    limit: int = 100,
    min_detections: int = 1,
    db: Session = Depends(get_db),
):
    """
    List all tracked unknown persons

    These are faces detected across multiple videos that haven't been identified yet
    """
    query = db.query(UnknownPerson).filter(
        UnknownPerson.is_active == 1,
        UnknownPerson.total_detections >= min_detections
    ).order_by(UnknownPerson.total_detections.desc())

    total = query.count()
    unknowns = query.offset(skip).limit(limit).all()

    unknown_list = []
    for unknown in unknowns:
        unknown_list.append({
            "id": unknown.id,
            "identifier": unknown.identifier,
            "total_detections": unknown.total_detections,
            "first_seen": unknown.first_seen,
            "last_seen": unknown.last_seen,
            "representative_image_path": unknown.representative_image_path,
            "notes": unknown.notes,
            "promoted_to_person_id": unknown.promoted_to_person_id,
        })

    return {
        "total": total,
        "unknown_persons": unknown_list,
        "message": f"Found {total} unknown persons tracked across videos"
    }


@router.get("/unknown-persons/{unknown_id}/timeline")
def get_unknown_person_timeline(
    unknown_id: int,
    db: Session = Depends(get_db),
):
    """
    Get detection timeline for a specific unknown person across all videos
    """
    unknown = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_id).first()

    if not unknown:
        raise HTTPException(status_code=404, detail="Unknown person not found")

    # Get all detections
    detections = db.query(Detection).filter(
        Detection.unknown_person_id == unknown_id
    ).order_by(Detection.timestamp.asc()).all()

    timeline = []
    videos_seen = set()

    for detection in detections:
        timeline.append({
            "timestamp": detection.timestamp,
            "video_name": detection.video_name,
            "frame_number": detection.frame_number,
            "confidence": detection.confidence,
            "detection_image_path": detection.detection_image_path,
        })
        videos_seen.add(detection.video_name)

    return {
        "unknown_person_id": unknown_id,
        "identifier": unknown.identifier,
        "total_detections": unknown.total_detections,
        "videos_appeared_in": len(videos_seen),
        "first_seen": unknown.first_seen,
        "last_seen": unknown.last_seen,
        "timeline": timeline,
    }


@router.post("/unknown-persons/{unknown_id}/promote")
def promote_unknown_to_person(
    unknown_id: int,
    name: str = Form(...),
    email: Optional[str] = Form(None),
    employee_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Promote an unknown person to a registered person

    Use this when you identify who the unknown person is.
    All their past detections will be linked to the new registered person.
    """
    from ...models.enhanced_database import Person

    unknown = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_id).first()

    if not unknown:
        raise HTTPException(status_code=404, detail="Unknown person not found")

    if unknown.promoted_to_person_id:
        raise HTTPException(status_code=400, detail="This unknown person has already been promoted")

    # Create new registered person using the unknown's face encoding
    person = Person(
        name=name,
        email=email,
        employee_id=employee_id,
        face_encoding=unknown.face_encoding,
        image_path=unknown.representative_image_path,
        notes=notes or f"Promoted from {unknown.identifier}",
        is_active=1,
    )

    db.add(person)
    db.flush()  # Get the person ID

    # Update all detections to point to the new person
    db.query(Detection).filter(
        Detection.unknown_person_id == unknown_id
    ).update({
        "person_id": person.id,
        "unknown_person_id": None,
        "detection_type": "registered"
    })

    # Mark unknown person as promoted
    unknown.promoted_to_person_id = person.id
    unknown.is_active = 0
    unknown.notes = f"Promoted to Person ID {person.id} ({name})"

    db.commit()
    db.refresh(person)

    return {
        "message": f"Successfully promoted {unknown.identifier} to registered person",
        "person_id": person.id,
        "person_name": name,
        "detections_transferred": unknown.total_detections,
    }
