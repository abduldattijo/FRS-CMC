"""
Video processor for cross-video identity linking system
Processes videos, detects faces, de-duplicates within video, and saves to database
"""

import cv2
import os
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import numpy as np
import pickle
from sqlalchemy.orm import Session

from .config import settings
# Using YOLO for better face detection (especially for West African faces)
try:
    from .yolo_face_detector import YOLOFaceDetector as FaceDetector
    print("✓ Using YOLO face detector")
except ImportError:
    # Fallback to MediaPipe if YOLO not available
    from .face_detector_mediapipe import FaceDetector
    print("⚠️  YOLO not available, using MediaPipe")
from .face_clustering import FaceClusterer
from ..models.cross_video_database import Video, VideoFace, RawDetection


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove characters that cause issues in URLs
    Replace #, ', ", and other problematic characters with underscores
    """
    # Remove or replace problematic characters
    filename = re.sub(r'[#\'\"<>{}|\\\^~\[\]`]', '_', filename)
    # Replace multiple consecutive underscores with single underscore
    filename = re.sub(r'_+', '_', filename)
    return filename


class CrossVideoProcessor:
    """
    Processes videos for cross-video analysis:
    1. Extract frames and detect faces
    2. Cluster faces within video to identify unique individuals
    3. Save to database for later cross-video matching
    """

    def __init__(self):
        """Initialize the cross-video processor"""
        self.face_detector = FaceDetector()
        # Threshold tuning for proper separation:
        # 0.92 = very strict (only identical faces)
        # 0.85 = balanced (same person in different lighting/angles)
        # Lower values group more aggressively
        self.face_clusterer = FaceClusterer(similarity_threshold=0.85)

    def get_video_info(self, video_path: str) -> Dict[str, any]:
        """Get information about a video file"""
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
        """Extract frames from a video"""
        frame_skip = frame_skip or settings.FRAME_SKIP
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        frame_count = 0
        extracted_count = 0

        base_time = datetime.now()

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            if frame_count % frame_skip == 0:
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
        db: Session,
        output_dir: Optional[str] = None,
        frame_skip: int = None,
        save_frames: bool = True,
    ) -> Dict[str, any]:
        """
        Process a video for cross-video analysis

        Args:
            video_path: Path to the video file
            db: Database session
            output_dir: Directory to save detection frames
            frame_skip: Process every Nth frame
            save_frames: Whether to save detection frames

        Returns:
            Dict with processing results
        """
        frame_skip = frame_skip or settings.FRAME_SKIP

        print(f"\n{'='*60}")
        print(f"Processing Video: {os.path.basename(video_path)}")
        print(f"{'='*60}\n")

        # Get video info
        video_info = self.get_video_info(video_path)
        video_filename = os.path.basename(video_path)

        # Create or get Video record
        video_record = db.query(Video).filter(Video.filename == video_filename).first()

        if video_record:
            # Update existing record
            video_record.processing_status = "processing"
            video_record.processing_started_at = datetime.utcnow()
            print(f"Updating existing video record (ID: {video_record.id})")
        else:
            # Create new record
            video_record = Video(
                filename=video_filename,
                filepath=video_path,
                duration_seconds=video_info["duration_seconds"],
                fps=video_info["fps"],
                total_frames=video_info["total_frames"],
                width=video_info["width"],
                height=video_info["height"],
                processing_status="processing",
                processing_started_at=datetime.utcnow()
            )
            db.add(video_record)
            db.flush()  # Get the video ID
            print(f"Created new video record (ID: {video_record.id})")

        db.commit()

        try:
            # Create output directory if needed
            if save_frames and output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            elif save_frames:
                output_dir = f"data/cross_video_detections/{video_record.id}"
                Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Extract frames
            print(f"Extracting frames (skip={frame_skip})...")
            frames = self.extract_frames(video_path, frame_skip=frame_skip)
            print(f"✓ Extracted {len(frames)} frames\n")

            # Detect faces in all frames
            print(f"Detecting faces in {len(frames)} frames...")
            all_detections = []
            frames_with_faces = 0

            for frame_number, frame, timestamp in frames:
                # Resize frame for faster processing
                processed_frame = self.face_detector.resize_image(frame)

                # Detect faces
                face_detections = self.face_detector.detect_faces(processed_frame)

                if len(face_detections) == 0:
                    continue

                frames_with_faces += 1

                # Handle different detector formats
                # YOLO returns list of dicts, MediaPipe returns list of tuples
                if isinstance(face_detections[0], dict):
                    # YOLO format: extract locations and use face_recognition for encoding
                    import face_recognition

                    # Convert to RGB for face_recognition
                    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)

                    for detection in face_detections:
                        face_location = detection['location']  # (top, right, bottom, left)
                        confidence = detection.get('confidence', 1.0)

                        # Get face encoding using face_recognition library
                        try:
                            face_encodings = face_recognition.face_encodings(
                                rgb_frame,
                                known_face_locations=[face_location]
                            )

                            if len(face_encodings) > 0:
                                face_encoding = face_encodings[0]

                                detection_dict = {
                                    "frame_number": frame_number,
                                    "timestamp": timestamp,
                                    "face_location": {
                                        "top": face_location[0],
                                        "right": face_location[1],
                                        "bottom": face_location[2],
                                        "left": face_location[3],
                                    },
                                    "face_encoding": face_encoding,
                                    "confidence": confidence,
                                    "frame": processed_frame,
                                }

                                all_detections.append(detection_dict)
                        except Exception as e:
                            # Skip faces that can't be encoded
                            continue
                else:
                    # MediaPipe format: original code
                    face_locations = face_detections

                    # Get face encodings
                    face_encodings = self.face_detector.get_face_encodings(
                        processed_frame, face_locations
                    )

                    # Store each detection
                    for idx, (face_location, face_encoding) in enumerate(
                        zip(face_locations, face_encodings)
                    ):
                        detection = {
                            "frame_number": frame_number,
                            "timestamp": timestamp,
                            "face_location": {
                                "top": face_location[0],
                                "right": face_location[1],
                                "bottom": face_location[2],
                                "left": face_location[3],
                            },
                            "face_encoding": face_encoding,
                            "confidence": 1.0,  # MediaPipe doesn't provide confidence, use 1.0
                            "frame": processed_frame,
                        }

                        all_detections.append(detection)

            print(f"✓ Detected {len(all_detections)} faces in {frames_with_faces} frames\n")

            if len(all_detections) == 0:
                video_record.processing_status = "completed"
                video_record.processing_completed_at = datetime.utcnow()
                video_record.total_faces_detected = 0
                video_record.unique_faces_count = 0
                db.commit()

                print("No faces detected in video.\n")
                return {
                    "video_id": video_record.id,
                    "total_detections": 0,
                    "unique_faces": 0,
                    "clusters": []
                }

            # Cluster faces to identify unique individuals
            print(f"Clustering faces to identify unique individuals...")
            clusters = self.face_clusterer.cluster_detections(all_detections)
            print(f"✓ Found {len(clusters)} unique individuals\n")

            # Save VideoFace entries and RawDetections
            print(f"Saving to database...")
            saved_faces = []

            for cluster_idx, cluster in enumerate(clusters, start=1):
                # Create face identifier (sanitize video filename for URL safety)
                safe_video_name = sanitize_filename(video_filename)
                face_identifier = f"{safe_video_name}_Person_{cluster_idx:03d}"

                # Save representative image
                if save_frames:
                    rep_detection = cluster["representative_detection"]
                    frame = rep_detection["frame"]
                    loc = rep_detection["face_location"]

                    # Draw bounding box
                    face_with_box = self.face_detector.draw_faces(
                        frame,
                        [(loc["top"], loc["right"], loc["bottom"], loc["left"])],
                        [f"Person {cluster_idx}"]
                    )

                    # Save
                    image_filename = f"{face_identifier}.jpg"
                    image_path = os.path.join(output_dir, image_filename)
                    cv2.imwrite(image_path, face_with_box)
                else:
                    image_path = None

                # Create VideoFace record
                video_face = VideoFace(
                    video_id=video_record.id,
                    face_identifier=face_identifier,
                    face_encoding=pickle.dumps(cluster["representative_encoding"]),
                    representative_image_path=image_path,
                    appearance_count=cluster["appearance_count"],
                    first_frame=cluster["first_frame"],
                    last_frame=cluster["last_frame"],
                    first_timestamp=cluster["first_timestamp"],
                    last_timestamp=cluster["last_timestamp"],
                    average_confidence=cluster["average_confidence"],
                    best_confidence=cluster["best_confidence"],
                )

                db.add(video_face)
                db.flush()  # Get the video_face ID

                # Save raw detections
                for detection in cluster["all_detections"]:
                    loc = detection["face_location"]

                    # Save detection image if needed
                    detection_image_path = None
                    if save_frames:
                        det_image_filename = f"{face_identifier}_frame_{detection['frame_number']}.jpg"
                        detection_image_path = os.path.join(output_dir, det_image_filename)

                        frame = detection["frame"]
                        face_with_box = self.face_detector.draw_faces(
                            frame,
                            [(loc["top"], loc["right"], loc["bottom"], loc["left"])],
                            [f"Person {cluster_idx}"]
                        )
                        cv2.imwrite(detection_image_path, face_with_box)

                    raw_detection = RawDetection(
                        video_face_id=video_face.id,
                        frame_number=detection["frame_number"],
                        timestamp=detection["timestamp"],
                        face_location_top=loc["top"],
                        face_location_right=loc["right"],
                        face_location_bottom=loc["bottom"],
                        face_location_left=loc["left"],
                        confidence=detection["confidence"],
                        face_encoding=pickle.dumps(detection["face_encoding"]),
                        detection_image_path=detection_image_path,
                    )

                    db.add(raw_detection)

                saved_faces.append({
                    "id": video_face.id,
                    "identifier": face_identifier,
                    "appearances": cluster["appearance_count"]
                })

                print(f"  ✓ {face_identifier}: {cluster['appearance_count']} appearances")

            # Update video record
            video_record.processing_status = "completed"
            video_record.processing_completed_at = datetime.utcnow()
            video_record.total_faces_detected = len(all_detections)
            video_record.unique_faces_count = len(clusters)

            db.commit()

            print(f"\n{'='*60}")
            print(f"Video Processing Complete!")
            print(f"Total detections: {len(all_detections)}")
            print(f"Unique individuals: {len(clusters)}")
            print(f"{'='*60}\n")

            return {
                "video_id": video_record.id,
                "video_filename": video_filename,
                "total_detections": len(all_detections),
                "unique_faces": len(clusters),
                "faces": saved_faces,
                "processing_time_seconds": (
                    video_record.processing_completed_at - video_record.processing_started_at
                ).total_seconds()
            }

        except Exception as e:
            # Mark as failed
            video_record.processing_status = "failed"
            video_record.processing_error = str(e)
            db.commit()

            print(f"\n{'='*60}")
            print(f"Video Processing Failed!")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")

            raise
