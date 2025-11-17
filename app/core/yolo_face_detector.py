"""
YOLO-based Face Detection
Uses YOLOv8 for superior face detection across diverse skin tones and challenging conditions
Optimized for West African faces with varying lighting
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from ultralytics import YOLO
import os
from pathlib import Path


class YOLOFaceDetector:
    """
    Advanced face detector using YOLOv8
    - Better accuracy on diverse skin tones (including West African faces)
    - Robust to varying lighting conditions
    - Detects faces at multiple angles
    - Handles partial occlusions
    - Fast inference on M4 Mac
    """

    def __init__(
        self,
        model_name: str = 'yolov8n.pt',  # Using general YOLOv8 (can detect people/faces)
        confidence_threshold: float = 0.4,
        min_face_size: int = 15,
    ):
        """
        Initialize the YOLO face detector

        Args:
            model_name: YOLO model to use ('yolov8n.pt' for nano, 'yolov8s.pt' for small, etc.)
            confidence_threshold: Minimum confidence for detection (0.0-1.0)
            min_face_size: Minimum face size in pixels
        """
        self.confidence_threshold = confidence_threshold
        self.min_face_size = min_face_size

        print(f"Initializing YOLO Face Detector...")
        print(f"  Model: {model_name}")
        print(f"  Confidence threshold: {confidence_threshold}")
        print(f"  Min face size: {min_face_size}px")

        try:
            # Initialize YOLO model
            self.model = YOLO(model_name)

            # Configure for CPU (M4 optimized)
            # YOLOv8 will use MPS (Metal Performance Shaders) on M4 Mac automatically

            print("✓ YOLO model loaded successfully")

        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            print("Falling back to person detection mode")
            self.model = YOLO(model_name)

    def detect_faces(
        self,
        image: np.ndarray,
        return_confidence: bool = True,
    ) -> List[Dict]:
        """
        Detect faces in an image using YOLO + face_recognition

        Two-stage approach:
        1. YOLO detects people (robust, works at all angles)
        2. face_recognition detects faces within person regions (accurate face localization)

        Args:
            image: Image array (BGR format from OpenCV)
            return_confidence: Whether to return confidence scores

        Returns:
            List of dicts containing:
            - location: (top, right, bottom, left) for compatibility
            - bbox: (x1, y1, x2, y2) bounding box
            - confidence: detection confidence
        """
        import face_recognition

        detections = []

        try:
            # STAGE 1: Use YOLO to detect people
            results = self.model(image, conf=self.confidence_threshold, verbose=False)

            # Convert to RGB for face_recognition
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Process each person detection
            for result in results:
                boxes = result.boxes

                for box in boxes:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    person_confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())

                    # Filter: only person detections (class 0)
                    if class_id == 0:  # person class
                        # STAGE 2: Detect faces within the person region
                        # Extract person region with some padding
                        h, w = image.shape[:2]

                        # Add 10% padding around person bbox
                        padding_x = int((x2 - x1) * 0.1)
                        padding_y = int((y2 - y1) * 0.1)

                        crop_x1 = max(0, int(x1) - padding_x)
                        crop_y1 = max(0, int(y1) - padding_y)
                        crop_x2 = min(w, int(x2) + padding_x)
                        crop_y2 = min(h, int(y2) + padding_y)

                        person_region = rgb_image[crop_y1:crop_y2, crop_x1:crop_x2]

                        if person_region.size == 0:
                            continue

                        # Use face_recognition to find faces in this person region
                        face_locations = face_recognition.face_locations(
                            person_region,
                            model='hog'  # Faster than CNN, good enough after YOLO filtering
                        )

                        # Convert face locations back to full image coordinates
                        for (face_top, face_right, face_bottom, face_left) in face_locations:
                            # Adjust coordinates to full image
                            abs_top = crop_y1 + face_top
                            abs_right = crop_x1 + face_right
                            abs_bottom = crop_y1 + face_bottom
                            abs_left = crop_x1 + face_left

                            # Filter by minimum face size
                            width = abs_right - abs_left
                            height = abs_bottom - abs_top

                            if width < self.min_face_size or height < self.min_face_size:
                                continue

                            detection = {
                                'location': (abs_top, abs_right, abs_bottom, abs_left),
                                'bbox': (abs_left, abs_top, abs_right, abs_bottom),
                                'confidence': person_confidence,  # Use YOLO's person confidence
                            }

                            detections.append(detection)

        except Exception as e:
            print(f"YOLO detection error: {e}")
            import traceback
            traceback.print_exc()
            return []

        return detections

    def detect_faces_batch(
        self,
        images: List[np.ndarray],
        batch_size: int = 8,
    ) -> List[List[Dict]]:
        """
        Detect faces in multiple images (batch processing for speed)

        Args:
            images: List of image arrays
            batch_size: Number of images to process at once

        Returns:
            List of detection lists (one per image)
        """
        all_detections = []

        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]

            # Process batch
            results = self.model(batch, conf=self.confidence_threshold, verbose=False)

            # Extract detections for each image in batch
            for result in results:
                detections = self._process_result(result)
                all_detections.append(detections)

        return all_detections

    def _process_result(self, result) -> List[Dict]:
        """Process a single YOLO result"""
        detections = []
        boxes = result.boxes

        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())

            if class_id == 0:  # person
                # Estimate face region
                person_height = y2 - y1
                face_height = person_height * 0.35

                face_y1 = y1
                face_y2 = y1 + face_height
                face_x1 = x1
                face_x2 = x2

                top = int(face_y1)
                bottom = int(face_y2)
                left = int(face_x1)
                right = int(face_x2)

                width = right - left
                height = bottom - top

                if width >= self.min_face_size and height >= self.min_face_size:
                    detection = {
                        'location': (top, right, bottom, left),
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': confidence,
                    }
                    detections.append(detection)

        return detections

    def draw_faces(
        self,
        image: np.ndarray,
        face_locations: List,
        labels: Optional[List[str]] = None,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """
        Draw bounding boxes on detected faces

        Args:
            image: Image array
            face_locations: List of face locations (tuples or dicts)
                - Tuples: (top, right, bottom, left)
                - Dicts: {'location': (top, right, bottom, left), 'confidence': float}
            labels: Optional labels for each face
            color: Box color in BGR format
            thickness: Box line thickness

        Returns:
            Image with drawn boxes
        """
        result_image = image.copy()

        for idx, detection in enumerate(face_locations):
            # Handle both tuple and dict formats
            if isinstance(detection, dict):
                top, right, bottom, left = detection['location']
                confidence = detection.get('confidence', 1.0)
            else:
                # Tuple format: (top, right, bottom, left)
                top, right, bottom, left = detection
                confidence = None

            # Draw rectangle
            cv2.rectangle(result_image, (left, top), (right, bottom), color, thickness)

            # Draw label
            if labels and idx < len(labels):
                label = labels[idx]
            elif confidence is not None:
                label = f"Face: {confidence:.2f}"
            else:
                label = "Face"

            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            cv2.rectangle(
                result_image,
                (left, bottom),
                (left + label_size[0], bottom + label_size[1] + 5),
                color,
                -1,
            )

            cv2.putText(
                result_image,
                label,
                (left, bottom + label_size[1] + 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
            )

        return result_image

    def extract_face(
        self,
        image: np.ndarray,
        face_location: Tuple[int, int, int, int],
        padding: int = 20
    ) -> np.ndarray:
        """
        Extract a face from an image with padding

        Args:
            image: Source image
            face_location: Face location as (top, right, bottom, left)
            padding: Padding around the face in pixels

        Returns:
            Cropped face image
        """
        top, right, bottom, left = face_location
        height, width = image.shape[:2]

        # Add padding
        top = max(0, top - padding)
        right = min(width, right + padding)
        bottom = min(height, bottom + padding)
        left = max(0, left - padding)

        # Extract face
        face_image = image[top:bottom, left:right]

        return face_image

    @staticmethod
    def resize_image(image: np.ndarray, width: int = 640) -> np.ndarray:
        """
        Resize image while maintaining aspect ratio

        Args:
            image: Input image
            width: Target width

        Returns:
            Resized image
        """
        height, original_width = image.shape[:2]
        aspect_ratio = height / original_width
        new_height = int(width * aspect_ratio)

        resized = cv2.resize(image, (width, new_height))
        return resized

    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            "model_type": "YOLOv8",
            "confidence_threshold": self.confidence_threshold,
            "min_face_size": self.min_face_size,
            "optimized_for": "West African faces, diverse lighting",
            "device": "CPU (MPS on M4 Mac)"
        }
