"""Pydantic schemas for request/response validation"""

from .person import PersonCreate, PersonResponse, PersonUpdate
from .recognition import DetectionResponse, VideoProcessRequest, RecognitionResult

__all__ = [
    "PersonCreate",
    "PersonResponse",
    "PersonUpdate",
    "DetectionResponse",
    "VideoProcessRequest",
    "RecognitionResult",
]
