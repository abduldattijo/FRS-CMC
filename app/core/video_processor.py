"""
Video processing functionality for extracting and processing frames from CCTV footage
"""

import cv2
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import numpy as np

from .config import settings

# Import TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .face_detector_mediapipe import FaceDetector
    from .face_recognizer_mediapipe import FaceRecognizer


class VideoProcessor:
    """
    Handles video file processing, frame extraction, and face detection in videos
    """

    def __init__(
        self,
        face_detector: "FaceDetector" = None,
        face_recognizer: "FaceRecognizer" = None,
    ):
        """
        Initialize the video processor

        Args:
            face_detector: FaceDetector instance
            face_recognizer: FaceRecognizer instance
        """
        if face_detector is None:
            # Import at runtime to avoid circular imports
            from .face_detector_mediapipe import FaceDetector as FD
            self.face_detector = FD()
        else:
            self.face_detector = face_detector

        if face_recognizer is None:
            # Import at runtime to avoid circular imports
            from .face_recognizer_mediapipe import FaceRecognizer as FR
            self.face_recognizer = FR()
        else:
            self.face_recognizer = face_recognizer

    def get_video_info(self, video_path: str) -> Dict[str, any]:
        """
        Get information about a video file

        Args:
            video_path: Path to the video file

        Returns:
            Dict with video metadata
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        info = {
            "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration_seconds": 0,
        }

        if info["fps"] > 0:
            info["duration_seconds"] = info["total_frames"] / info["fps"]

        cap.release()
        return info

    def extract_frames(
        self,
        video_path: str,
        frame_skip: int = None,
        max_frames: Optional[int] = None,
    ) -> List[Tuple[int, np.ndarray, datetime]]:
        """
        Extract frames from a video

        Args:
            video_path: Path to the video file
            frame_skip: Process every Nth frame (default from settings)
            max_frames: Maximum number of frames to extract

        Returns:
            List of tuples (frame_number, frame_image, timestamp)
        """
        frame_skip = frame_skip or settings.FRAME_SKIP
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        frame_count = 0
        extracted_count = 0

        # Get video start time (use current time as base if not available)
        base_time = datetime.now()

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            # Process every Nth frame
            if frame_count % frame_skip == 0:
                # Calculate timestamp based on frame number and FPS
                if fps > 0:
                    timestamp = base_time + timedelta(seconds=frame_count / fps)
                else:
                    timestamp = base_time

                frames.append((frame_count, frame, timestamp))
                extracted_count += 1

                if max_frames and extracted_count >= max_frames:
                    break

            frame_count += 1

        cap.release()
        return frames

    def process_video(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        frame_skip: int = None,
        save_frames: bool = None,
        confidence_threshold: float = None,
    ) -> Dict[str, any]:
        """
        Process a video for face detection and recognition

        Args:
            video_path: Path to the video file
            output_dir: Directory to save detection frames
            frame_skip: Process every Nth frame
            save_frames: Whether to save detection frames
            confidence_threshold: Minimum confidence for recognition

        Returns:
            Dict with processing results
        """
        frame_skip = frame_skip or settings.FRAME_SKIP
        save_frames = save_frames if save_frames is not None else settings.SAVE_FRAMES
        confidence_threshold = confidence_threshold or settings.CONFIDENCE_THRESHOLD

        # Create output directory if needed
        if save_frames and output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get video info
        video_info = self.get_video_info(video_path)
        video_name = os.path.basename(video_path)

        # Extract frames
        print(f"Extracting frames from {video_name}...")
        frames = self.extract_frames(video_path, frame_skip=frame_skip)

        # Process frames
        detections = []
        start_time = datetime.now()

        print(f"Processing {len(frames)} frames...")
        for frame_number, frame, timestamp in frames:
            # Resize frame for faster processing
            processed_frame = self.face_detector.resize_image(frame)

            # Detect faces
            face_locations = self.face_detector.detect_faces(processed_frame)

            if len(face_locations) == 0:
                continue

            # Get face encodings
            face_encodings = self.face_detector.get_face_encodings(
                processed_frame, face_locations
            )

            # Recognize faces
            recognition_results = self.face_recognizer.recognize_faces(face_encodings)

            # Process each detection
            for idx, (face_location, recognition) in enumerate(
                zip(face_locations, recognition_results)
            ):
                # Skip if below confidence threshold
                if recognition["confidence"] < confidence_threshold and not recognition["is_unknown"]:
                    continue

                detection = {
                    "frame_number": frame_number,
                    "timestamp": timestamp,
                    "person_id": recognition["person_id"],
                    "person_name": recognition["person_name"],
                    "confidence": recognition["confidence"],
                    "is_unknown": recognition["is_unknown"],
                    "face_location": {
                        "top": face_location[0],
                        "right": face_location[1],
                        "bottom": face_location[2],
                        "left": face_location[3],
                    },
                    "detection_image_path": None,
                }

                # Save detection frame if enabled
                if save_frames and output_dir:
                    # Draw bounding box
                    label = f"{recognition['person_name']} ({recognition['confidence']:.2f})"
                    frame_with_box = self.face_detector.draw_faces(
                        processed_frame, [face_location], [label]
                    )

                    # Save frame
                    frame_filename = f"detection_{frame_number}_{idx}_{recognition['person_name']}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    cv2.imwrite(frame_path, frame_with_box)
                    detection["detection_image_path"] = frame_path

                detections.append(detection)

        processing_time = (datetime.now() - start_time).total_seconds()

        # Calculate statistics
        known_detections = [d for d in detections if not d["is_unknown"]]
        unknown_detections = [d for d in detections if d["is_unknown"]]

        result = {
            "video_name": video_name,
            "total_frames": video_info["total_frames"],
            "processed_frames": len(frames),
            "total_detections": len(detections),
            "known_detections": len(known_detections),
            "unknown_detections": len(unknown_detections),
            "processing_time_seconds": processing_time,
            "detections": detections,
        }

        print(f"Processing complete! Found {len(detections)} detections in {processing_time:.2f}s")
        return result

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[List[Tuple[int, int, int, int]], List[Dict[str, any]]]:
        """
        Process a single frame for face detection and recognition

        Args:
            frame: Frame image

        Returns:
            Tuple of (face_locations, recognition_results)
        """
        # Resize for faster processing
        processed_frame = self.face_detector.resize_image(frame)

        # Detect faces
        face_locations = self.face_detector.detect_faces(processed_frame)

        if len(face_locations) == 0:
            return [], []

        # Get encodings
        face_encodings = self.face_detector.get_face_encodings(
            processed_frame, face_locations
        )

        # Recognize faces
        recognition_results = self.face_recognizer.recognize_faces(face_encodings)

        return face_locations, recognition_results
