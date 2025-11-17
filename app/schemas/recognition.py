"""
Pydantic schemas for Recognition and Detection operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FaceLocation(BaseModel):
    """Schema for face location in frame"""

    top: int
    right: int
    bottom: int
    left: int


class RecognitionResult(BaseModel):
    """Schema for a single face recognition result"""

    person_id: Optional[int] = None
    person_name: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence score")
    is_unknown: bool = Field(default=False, description="Whether the person is unknown")
    face_location: FaceLocation
    frame_number: int
    timestamp: datetime


class DetectionResponse(BaseModel):
    """Schema for detection record response"""

    id: int
    person_id: Optional[int]
    person_name: Optional[str]
    video_name: str
    frame_number: int
    timestamp: datetime
    confidence: Optional[float]
    face_location: Optional[FaceLocation]
    detection_image_path: Optional[str]
    is_unknown: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VideoProcessRequest(BaseModel):
    """Schema for video processing request"""

    save_frames: bool = Field(default=True, description="Save detection frames")
    frame_skip: Optional[int] = Field(
        default=5, ge=1, description="Process every Nth frame"
    )
    confidence_threshold: Optional[float] = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum confidence for recognition"
    )


class VideoProcessResponse(BaseModel):
    """Schema for video processing response"""

    video_name: str
    total_frames: int
    processed_frames: int
    total_detections: int
    known_detections: int
    unknown_detections: int
    processing_time_seconds: float
    detections: List[RecognitionResult]


class DetectionListResponse(BaseModel):
    """Schema for list of detections"""

    total: int
    detections: List[DetectionResponse]


class DetectionStats(BaseModel):
    """Schema for detection statistics"""

    total_detections: int
    known_persons: int
    unknown_persons: int
    detections_by_person: dict
    detections_by_date: dict
