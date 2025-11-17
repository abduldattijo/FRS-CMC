"""
Enhanced video processor that tracks unknown persons across videos
"""

import cv2
import os
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import numpy as np
from sqlalchemy.orm import Session

from .config import settings
from .face_detector_mediapipe import FaceDetector
from .enhanced_recognizer import EnhancedFaceRecognizer
from ..models.enhanced_database import Detection, UnknownPerson


class EnhancedVideoProcessor:
    """
    Video processor that tracks both registered AND unknown persons across videos
    """

    def __init__(
        self,
        face_detector: FaceDetector = None,
        face_recognizer: EnhancedFaceRecognizer = None,
    ):
        """Initialize the enhanced video processor"""
        self.face_detector = face_detector or FaceDetector()
        self.face_recognizer = face_recognizer or EnhancedFaceRecognizer()

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

    def process_video_with_tracking(
        self,
        video_path: str,
        db: Session,
        output_dir: Optional[str] = None,
        frame_skip: int = None,
        save_frames: bool = None,
        confidence_threshold: float = None,
    ) -> Dict[str, any]:
        """
        Process video and track ALL faces (registered + unknown) across videos

        Args:
            video_path: Path to video file
            db: Database session (REQUIRED for tracking)
            output_dir: Directory to save detection frames
            frame_skip: Process every Nth frame
            save_frames: Whether to save detection frames
            confidence_threshold: Minimum confidence for registered persons

        Returns:
            Dict with processing results including unknown person tracking
        """
        frame_skip = frame_skip or settings.FRAME_SKIP
        save_frames = save_frames if save_frames is not None else settings.SAVE_FRAMES
        confidence_threshold = confidence_threshold or settings.CONFIDENCE_THRESHOLD

        # Create output directory if needed
        if save_frames and output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Load ALL known faces (registered + unknown from previous videos)
        print("Loading known faces...")
        loaded_faces = self.face_recognizer.load_all_known_faces(db)
        print(f"  Registered persons: {loaded_faces['registered']}")
        print(f"  Tracked unknowns: {loaded_faces['unknown_tracked']}")
        print(f"  Total faces to match: {loaded_faces['total']}")

        # Get video info
        video_info = self.get_video_info(video_path)
        video_name = os.path.basename(video_path)

        # Extract frames
        print(f"\nExtracting frames from {video_name}...")
        frames = self.extract_frames(video_path, frame_skip=frame_skip)

        # Process frames
        detections = []
        new_unknowns_created = 0
        new_unknown_ids = []  # Track IDs of unknowns created in THIS video
        start_time = datetime.now()

        print(f"\nProcessing {len(frames)} frames...")
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

            # Recognize faces (checks registered + unknown persons)
            recognition_results = self.face_recognizer.recognize_faces(face_encodings, db)

            # Process each detection
            for idx, (face_location, recognition) in enumerate(
                zip(face_locations, recognition_results)
            ):
                detection_data = {
                    "frame_number": frame_number,
                    "timestamp": timestamp,
                    "face_location": {
                        "top": face_location[0],
                        "right": face_location[1],
                        "bottom": face_location[2],
                        "left": face_location[3],
                    },
                    "detection_image_path": None,
                }

                # Handle different detection types
                if recognition["detection_type"] == "registered":
                    # Matched to a REGISTERED person
                    detection_data.update({
                        "person_id": recognition["person_id"],
                        "person_name": recognition["person_name"],
                        "unknown_person_id": None,
                        "unknown_identifier": None,
                        "confidence": recognition["confidence"],
                        "detection_type": "registered"
                    })

                elif recognition["detection_type"] == "unknown_tracked":
                    # Matched to an UNKNOWN person from previous videos
                    detection_data.update({
                        "person_id": None,
                        "person_name": None,
                        "unknown_person_id": recognition["unknown_person_id"],
                        "unknown_identifier": recognition["unknown_identifier"],
                        "confidence": recognition["confidence"],
                        "detection_type": "unknown_tracked"
                    })

                    # Update sighting count
                    self.face_recognizer.update_unknown_person_sighting(
                        recognition["unknown_person_id"], db, timestamp
                    )

                elif recognition["detection_type"] == "unknown_new":
                    # NEW unknown person - create database entry
                    detection_image_path = None

                    if save_frames and output_dir:
                        # Save the face image
                        frame_filename = f"unknown_{frame_number}_{idx}.jpg"
                        frame_path = os.path.join(output_dir, frame_filename)

                        # Draw bounding box
                        frame_with_box = self.face_detector.draw_faces(
                            processed_frame, [face_location], ["New Unknown"]
                        )
                        cv2.imwrite(frame_path, frame_with_box)
                        detection_image_path = frame_path

                    # Create new unknown person in database
                    unknown_person = self.face_recognizer.create_unknown_person(
                        recognition["encoding"],
                        db,
                        first_detection_info={
                            'image_path': detection_image_path,
                            'timestamp': timestamp
                        }
                    )

                    new_unknowns_created += 1
                    new_unknown_ids.append(unknown_person.id)  # Track for clustering

                    detection_data.update({
                        "person_id": None,
                        "person_name": None,
                        "unknown_person_id": unknown_person.id,
                        "unknown_identifier": unknown_person.identifier,
                        "confidence": 0.0,
                        "detection_type": "unknown_new"
                    })

                # Save detection frame if enabled
                if save_frames and output_dir and not detection_data["detection_image_path"]:
                    label = detection_data.get("person_name") or detection_data.get("unknown_identifier", "Unknown")
                    confidence_label = f" ({detection_data['confidence']:.2f})" if detection_data['confidence'] > 0 else ""

                    frame_with_box = self.face_detector.draw_faces(
                        processed_frame, [face_location], [label + confidence_label]
                    )

                    frame_filename = f"detection_{frame_number}_{idx}.jpg"
                    frame_path = os.path.join(output_dir, frame_filename)
                    cv2.imwrite(frame_path, frame_with_box)
                    detection_data["detection_image_path"] = frame_path

                detections.append(detection_data)

        processing_time = (datetime.now() - start_time).total_seconds()

        # CLUSTER DUPLICATES: Merge unknown persons that are the same person
        # This ensures same person appearing multiple times = 1 database entry
        clustering_stats = {"duplicates_merged": 0, "unique_after_clustering": new_unknowns_created}
        if len(new_unknown_ids) > 1:
            print(f"\nClustering {len(new_unknown_ids)} new unknowns to merge duplicates...")
            clustering_stats = self.face_recognizer.cluster_and_merge_duplicates(
                new_unknown_ids, db
            )
            print(f"  Before clustering: {clustering_stats['total_input']} unknowns")
            print(f"  After clustering: {clustering_stats['unique_after_clustering']} unique unknowns")
            print(f"  Duplicates merged: {clustering_stats['duplicates_merged']}")

        # Calculate statistics
        registered_detections = [d for d in detections if d["detection_type"] == "registered"]
        tracked_unknown_detections = [d for d in detections if d["detection_type"] == "unknown_tracked"]
        new_unknown_detections = [d for d in detections if d["detection_type"] == "unknown_new"]

        result = {
            "video_name": video_name,
            "total_frames": video_info["total_frames"],
            "processed_frames": len(frames),
            "total_detections": len(detections),
            "registered_detections": len(registered_detections),
            "tracked_unknown_detections": len(tracked_unknown_detections),
            "new_unknown_detections": len(new_unknown_detections),
            "new_unknowns_created": clustering_stats['unique_after_clustering'],  # After clustering
            "duplicates_merged": clustering_stats['duplicates_merged'],
            "processing_time_seconds": processing_time,
            "detections": detections,
        }

        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"  Total detections: {len(detections)}")
        print(f"  - Registered persons: {len(registered_detections)}")
        print(f"  - From previous videos: {len(tracked_unknown_detections)}")
        print(f"  - New unique unknowns: {clustering_stats['unique_after_clustering']}")
        if clustering_stats['duplicates_merged'] > 0:
            print(f"    (Merged {clustering_stats['duplicates_merged']} duplicates from same video)")
        print(f"  Processing time: {processing_time:.2f}s")
        print(f"{'='*60}\n")

        return result
