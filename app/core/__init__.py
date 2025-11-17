"""Core functionality modules"""

from .config import settings

# Lazy imports to avoid dependency conflicts at startup
# Import face detector and recognizer only when needed
FaceDetector = None
FaceRecognizer = None

try:
    # Try MediaPipe-based implementations first (M4 Mac compatible)
    from .face_detector_mediapipe import FaceDetector
    from .face_recognizer_mediapipe import FaceRecognizer
    _implementation = "mediapipe"
except ImportError as e:
    try:
        # Fallback to dlib-based implementation
        from .face_detector import FaceDetector
        from .face_recognizer import FaceRecognizer
        _implementation = "dlib"
    except ImportError:
        # If both fail, set to None and warn
        print(f"Warning: Could not import face detection/recognition modules")
        print(f"MediaPipe error: {e}")
        _implementation = "none"

from .video_processor import VideoProcessor

__all__ = ["settings", "FaceDetector", "FaceRecognizer", "VideoProcessor"]
