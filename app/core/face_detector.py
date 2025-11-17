"""
Face detection functionality using face_recognition library
"""

import face_recognition
import cv2
import numpy as np
from typing import List, Tuple, Optional
from .config import settings


class FaceDetector:
    """
    Handles face detection in images and video frames
    """

    def __init__(
        self,
        model: str = None,
        min_face_size: int = None,
    ):
        """
        Initialize the face detector

        Args:
            model: Detection model ('hog' for CPU, 'cnn' for GPU)
            min_face_size: Minimum face size in pixels
        """
        self.model = model or settings.DETECTION_METHOD
        self.min_face_size = min_face_size or settings.MIN_FACE_SIZE

    def detect_faces(
        self, image: np.ndarray, number_of_times_to_upsample: int = 1
    ) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image

        Args:
            image: Image array (BGR format from OpenCV)
            number_of_times_to_upsample: How many times to upsample for detection

        Returns:
            List of face locations as (top, right, bottom, left) tuples
        """
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Detect faces
        face_locations = face_recognition.face_locations(
            rgb_image,
            number_of_times_to_upsample=number_of_times_to_upsample,
            model=self.model,
        )

        # Filter by minimum face size
        filtered_locations = []
        for top, right, bottom, left in face_locations:
            width = right - left
            height = bottom - top
            if width >= self.min_face_size and height >= self.min_face_size:
                filtered_locations.append((top, right, bottom, left))

        return filtered_locations

    def get_face_encodings(
        self,
        image: np.ndarray,
        face_locations: Optional[List[Tuple[int, int, int, int]]] = None,
        num_jitters: int = None,
    ) -> List[np.ndarray]:
        """
        Get face encodings for detected faces

        Args:
            image: Image array (BGR format)
            face_locations: Known face locations, or None to detect automatically
            num_jitters: Number of times to re-sample for encoding

        Returns:
            List of 128-dimensional face encodings
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # If no face locations provided, detect them
        if face_locations is None:
            face_locations = self.detect_faces(image)

        # Get encodings
        num_jitters = num_jitters or settings.NUM_JITTERS
        encodings = face_recognition.face_encodings(
            rgb_image, known_face_locations=face_locations, num_jitters=num_jitters
        )

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
