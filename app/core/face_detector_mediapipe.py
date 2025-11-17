"""
Face detection functionality using MediaPipe (Apple Silicon M4 optimized)
"""

import mediapipe as mp
import cv2
import numpy as np
from typing import List, Tuple, Optional
from .config import settings


class FaceDetector:
    """
    Handles face detection in images and video frames using MediaPipe
    """

    def __init__(
        self,
        model: str = None,
        min_face_size: int = None,
        detection_confidence: float = 0.5,
    ):
        """
        Initialize the face detector

        Args:
            model: Not used (kept for compatibility)
            min_face_size: Minimum face size in pixels
            detection_confidence: Minimum detection confidence (0.0-1.0)
        """
        self.min_face_size = min_face_size or settings.MIN_FACE_SIZE
        self.detection_confidence = detection_confidence

        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # 1 for full range, 0 for short range
            min_detection_confidence=detection_confidence
        )
        # Face mesh for landmarks (used for encoding)
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=10,
            min_detection_confidence=detection_confidence
        )

    def detect_faces(
        self, image: np.ndarray, number_of_times_to_upsample: int = 1
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image

        Args:
            image: Image array (BGR format from OpenCV)
            number_of_times_to_upsample: Not used (kept for compatibility)

        Returns:
            List of face locations as (top, right, bottom, left) tuples
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]

        # Detect faces
        results = self.face_detection.process(rgb_image)

        face_locations = []
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box

                # Convert relative coordinates to absolute
                left = int(bboxC.xmin * width)
                top = int(bboxC.ymin * height)
                right = int((bboxC.xmin + bboxC.width) * width)
                bottom = int((bboxC.ymin + bboxC.height) * height)

                # Ensure coordinates are within image bounds
                left = max(0, left)
                top = max(0, top)
                right = min(width, right)
                bottom = min(height, bottom)

                # Check minimum face size
                face_width = right - left
                face_height = bottom - top

                if face_width >= self.min_face_size and face_height >= self.min_face_size:
                    # Return in (top, right, bottom, left) format for compatibility
                    face_locations.append((top, right, bottom, left))

        return face_locations

    def get_face_encodings(
        self,
        image: np.ndarray,
        face_locations: Optional[List[Tuple[int, int, int, int]]] = None,
        num_jitters: int = None,
    ) -> List[np.ndarray]:
        """
        Get face encodings for detected faces using MediaPipe Face Mesh landmarks

        Args:
            image: Image array (BGR format)
            face_locations: Known face locations, or None to detect automatically
            num_jitters: Not used (kept for compatibility)

        Returns:
            List of face encodings (468-dimensional landmark vectors)
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # If no face locations provided, detect them
        if face_locations is None:
            face_locations = self.detect_faces(image)

        encodings = []
        height, width = image.shape[:2]

        # Process each face
        for top, right, bottom, left in face_locations:
            # Crop face region
            face_img = rgb_image[top:bottom, left:right]

            if face_img.size == 0:
                continue

            # Get face mesh landmarks
            results = self.face_mesh.process(face_img)

            if results.multi_face_landmarks:
                # Use first face's landmarks
                landmarks = results.multi_face_landmarks[0]

                # Extract landmark coordinates as encoding
                # MediaPipe provides 468 landmarks, we'll use their normalized coordinates
                encoding = []
                for landmark in landmarks.landmark:
                    encoding.extend([landmark.x, landmark.y, landmark.z])

                encodings.append(np.array(encoding, dtype=np.float64))

        return encodings

    def draw_faces(
        self,
        image: np.ndarray,
        face_locations: List[Tuple[int, int, int, int]],
        labels: Optional[List[str]] = None,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """
        Draw bounding boxes around detected faces

        Args:
            image: Image array
            face_locations: List of face locations
            labels: Optional labels for each face
            color: Box color in BGR format
            thickness: Box line thickness

        Returns:
            Image with drawn boxes
        """
        result_image = image.copy()

        for idx, (top, right, bottom, left) in enumerate(face_locations):
            # Draw rectangle
            cv2.rectangle(result_image, (left, top), (right, bottom), color, thickness)

            # Draw label if provided
            if labels and idx < len(labels):
                label = labels[idx]
                # Draw label background
                label_size, _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
                )
                cv2.rectangle(
                    result_image,
                    (left, bottom),
                    (left + label_size[0], bottom + label_size[1] + 10),
                    color,
                    -1,
                )
                # Draw label text
                cv2.putText(
                    result_image,
                    label,
                    (left, bottom + label_size[1] + 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                )

        return result_image

    def extract_face(
        self, image: np.ndarray, face_location: Tuple[int, int, int, int], padding: int = 20
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
    def resize_image(image: np.ndarray, width: int = None) -> np.ndarray:
        """
        Resize image while maintaining aspect ratio

        Args:
            image: Input image
            width: Target width (height will be calculated)

        Returns:
            Resized image
        """
        if width is None:
            width = settings.RESIZE_WIDTH

        height, original_width = image.shape[:2]
        aspect_ratio = height / original_width
        new_height = int(width * aspect_ratio)

        resized = cv2.resize(image, (width, new_height))
        return resized

    def __del__(self):
        """Cleanup MediaPipe resources"""
        if hasattr(self, 'face_detection'):
            self.face_detection.close()
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
