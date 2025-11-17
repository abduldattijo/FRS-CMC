"""
API routes for video processing and CCTV footage analysis
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import shutil
import os
from datetime import datetime

from ...models.enhanced_database import Detection
from ...schemas.recognition import VideoProcessResponse, VideoProcessRequest
from ...core.config import settings
from ...core.video_processor import VideoProcessor
from ...core import FaceDetector, FaceRecognizer  # Use MediaPipe versions
from ..dependencies import get_db

router = APIRouter(prefix="/video", tags=["Video Processing"])


@router.post("/process", response_model=VideoProcessResponse)
async def process_video(
    video: UploadFile = File(...),
    frame_skip: Optional[int] = Form(None),
    save_frames: Optional[bool] = Form(True),
    confidence_threshold: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Process a CCTV video file for face detection and recognition

    Args:
        video: Video file to process
        frame_skip: Process every Nth frame (default from config)
        save_frames: Whether to save detection frames
        confidence_threshold: Minimum confidence for recognition
        db: Database session

    Returns:
        Processing results with detections
    """
    # Validate video file
    file_ext = os.path.splitext(video.filename)[1].lower()
    if file_ext not in settings.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format. Supported formats: {settings.SUPPORTED_FORMATS}",
        )

    # Check file size
    video.file.seek(0, 2)  # Seek to end
    file_size = video.file.tell()
    video.file.seek(0)  # Reset to beginning

    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB",
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
        face_recognizer = FaceRecognizer()

        # Load known faces from database
        known_faces_count = face_recognizer.load_known_faces(db)
        print(f"Loaded {known_faces_count} known faces from database")

        # Initialize video processor
        video_processor = VideoProcessor(face_detector, face_recognizer)

        # Create output directory for detections
        output_dir = None
        if save_frames:
            output_dir = os.path.join(
                settings.DETECTIONS_DIR, f"{timestamp}_{os.path.splitext(video.filename)[0]}"
            )

        # Process the video
        result = video_processor.process_video(
            video_path=video_path,
            output_dir=output_dir,
            frame_skip=frame_skip,
            save_frames=save_frames,
            confidence_threshold=confidence_threshold,
        )

        # Save detections to database
        for detection_data in result["detections"]:
            detection = Detection(
                person_id=detection_data["person_id"],
                video_name=video_filename,
                video_path=video_path,
                frame_number=detection_data["frame_number"],
                timestamp=detection_data["timestamp"],
                confidence=detection_data["confidence"],
                face_location_top=detection_data["face_location"]["top"],
                face_location_right=detection_data["face_location"]["right"],
                face_location_bottom=detection_data["face_location"]["bottom"],
                face_location_left=detection_data["face_location"]["left"],
                detection_image_path=detection_data["detection_image_path"],
                is_unknown=1 if detection_data["is_unknown"] else 0,
            )
            db.add(detection)

        db.commit()

        # Format response
        response = {
            "video_name": video_filename,
            "total_frames": result["total_frames"],
            "processed_frames": result["processed_frames"],
            "total_detections": result["total_detections"],
            "known_detections": result["known_detections"],
            "unknown_detections": result["unknown_detections"],
            "processing_time_seconds": result["processing_time_seconds"],
            "detections": [
                {
                    "person_id": d["person_id"],
                    "person_name": d["person_name"],
                    "confidence": d["confidence"],
                    "is_unknown": d["is_unknown"],
                    "face_location": d["face_location"],
                    "frame_number": d["frame_number"],
                    "timestamp": d["timestamp"],
                }
                for d in result["detections"]
            ],
        }

        return response

    except Exception as e:
        # Clean up video file on error
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")


@router.get("/uploads")
def list_uploaded_videos(db: Session = Depends(get_db)):
    """
    List all uploaded videos

    Returns:
        List of uploaded video files
    """
    videos = []

    for filename in os.listdir(settings.UPLOADS_DIR):
        if filename.endswith(tuple(settings.SUPPORTED_FORMATS)):
            file_path = os.path.join(settings.UPLOADS_DIR, filename)
            file_stat = os.stat(file_path)

            videos.append(
                {
                    "filename": filename,
                    "size_mb": file_stat.st_size / (1024 * 1024),
                    "uploaded_at": datetime.fromtimestamp(file_stat.st_ctime),
                }
            )

    return {"total": len(videos), "videos": videos}


@router.delete("/uploads/{filename}")
def delete_video(filename: str, db: Session = Depends(get_db)):
    """
    Delete an uploaded video file

    Args:
        filename: Video filename
        db: Database session
    """
    video_path = os.path.join(settings.UPLOADS_DIR, filename)

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    # Delete the file
    os.remove(video_path)

    # Also delete associated detections (optional - could be soft delete)
    db.query(Detection).filter(Detection.video_name == filename).delete()
    db.commit()

    return {"message": f"Video {filename} deleted successfully"}
