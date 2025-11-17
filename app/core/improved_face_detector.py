"""
Improved Face Detection using RetinaFace
Optimized for West African faces with darker skin tones and varying lighting conditions
Includes quality scoring for each detected face
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from retinaface import RetinaFace
from skimage import filters
from .config import settings


class ImprovedFaceDetector:
    """
    Advanced face detector using RetinaFace with quality assessment
    Optimized for diverse skin tones and challenging lighting conditions
    """

    def __init__(
        self,
        min_face_size: int = None,
        confidence_threshold: float = 0.9,
    ):
        """
        Initialize the improved face detector

        Args:
            min_face_size: Minimum face size in pixels
            confidence_threshold: Minimum confidence for face detection (0.0-1.0)
        """
        self.min_face_size = min_face_size or settings.MIN_FACE_SIZE
        self.confidence_threshold = confidence_threshold
        print("✓ ImprovedFaceDetector initialized with RetinaFace")

    def detect_faces(
        self,
        image: np.ndarray,
        return_quality_scores: bool = True,
    ) -> List[Dict]:
        """
        Detect faces in an image using RetinaFace

        Args:
            image: Image array (BGR format from OpenCV)
            return_quality_scores: Whether to compute quality scores

        Returns:
            List of dicts containing:
            - bbox: (x, y, w, h) bounding box
            - location: (top, right, bottom, left) for compatibility
            - confidence: detection confidence
            - landmarks: facial landmarks (5 points)
            - quality_score: overall quality (0.0-1.0)
            - blur_score: image sharpness
            - size_score: face size adequacy
            - angle_score: face orientation quality
        """
        # RetinaFace expects RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image

        # Detect faces using RetinaFace
        # RetinaFace is trained on diverse datasets and performs better on darker skin tones
        try:
            detections = RetinaFace.detect_faces(rgb_image, threshold=self.confidence_threshold)
        except Exception as e:
            print(f"RetinaFace detection error: {e}")
            return []

        if not isinstance(detections, dict):
            return []

        results = []

        for face_key, face_data in detections.items():
            # Extract bounding box
            facial_area = face_data['facial_area']
            x, y, w, h = facial_area[0], facial_area[1], facial_area[2], facial_area[3]

            # Convert to (top, right, bottom, left) format for compatibility
            top, left = y, x
            bottom, right = h, w

            # Filter by minimum face size
            face_width = right - left
            face_height = bottom - top

            if face_width < self.min_face_size or face_height < self.min_face_size:
                continue

            face_info = {
                'bbox': (x, y, w, h),
                'location': (top, right, bottom, left),
                'confidence': face_data['score'],
                'landmarks': face_data.get('landmarks', {}),
            }

            # Compute quality scores if requested
            if return_quality_scores:
                quality_metrics = self.compute_face_quality(
                    image, (top, right, bottom, left), face_data.get('landmarks', {})
                )
                face_info.update(quality_metrics)

            results.append(face_info)

        return results

    def compute_face_quality(
        self,
        image: np.ndarray,
        face_location: Tuple[int, int, int, int],
        landmarks: Dict
    ) -> Dict[str, float]:
        """
        Compute quality scores for a detected face

        Args:
            image: Full image
            face_location: (top, right, bottom, left) face coordinates
            landmarks: Facial landmarks from RetinaFace

        Returns:
            Dict with quality metrics:
            - quality_score: overall quality (0.0-1.0)
            - blur_score: sharpness score (higher is better)
            - size_score: face size adequacy (0.0-1.0)
            - angle_score: face orientation quality (0.0-1.0)
        """
        top, right, bottom, left = face_location

        # 1. BLUR DETECTION (Laplacian variance method)
        face_crop = image[top:bottom, left:right]
        if face_crop.size == 0:
            return self._default_quality_scores()

        gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
        blur_score = self._compute_blur_score(gray_face)

        # 2. SIZE SCORE (based on face area relative to image)
        size_score = self._compute_size_score(face_location, image.shape)

        # 3. ANGLE SCORE (face pose estimation from landmarks)
        angle_score = self._compute_angle_score(landmarks)

        # 4. OVERALL QUALITY (weighted combination)
        # Weights optimized for West African face recognition in varying lighting
        quality_score = (
            0.4 * blur_score +      # Blur is most important
            0.3 * size_score +       # Size matters for recognition
            0.3 * angle_score        # Frontal faces work best
        )

        return {
            'quality_score': float(quality_score),
            'blur_score': float(blur_score),
            'size_score': float(size_score),
            'angle_score': float(angle_score),
        }

    def _compute_blur_score(self, gray_image: np.ndarray) -> float:
        """
        Compute image sharpness using Laplacian variance
        Higher values = sharper image

        Returns:
            Normalized blur score (0.0-1.0)
        """
        if gray_image.size == 0:
            return 0.0

        # Compute Laplacian variance
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F)
        variance = laplacian.var()

        # Normalize to 0-1 range (empirical thresholds)
        # Values below 100 are typically blurry, above 500 are sharp
        normalized = min(variance / 500.0, 1.0)

        return normalized

    def _compute_size_score(
        self,
        face_location: Tuple[int, int, int, int],
        image_shape: Tuple[int, int]
    ) -> float:
        """
        Compute face size score relative to image size
        Larger faces (closer to camera) generally have better quality

        Returns:
            Size score (0.0-1.0)
        """
        top, right, bottom, left = face_location
        face_height = bottom - top
        face_width = right - left
        face_area = face_height * face_width

        image_height, image_width = image_shape[:2]
        image_area = image_height * image_width

        # Face should ideally be 5-30% of image area
        area_ratio = face_area / image_area

        if area_ratio < 0.01:  # Too small
            return area_ratio / 0.01  # Linear scale up to 1%
        elif area_ratio < 0.05:  # Small but acceptable
            return 0.6 + (area_ratio - 0.01) / 0.04 * 0.2  # 0.6 to 0.8
        elif area_ratio < 0.30:  # Ideal range
            return 0.8 + (area_ratio - 0.05) / 0.25 * 0.2  # 0.8 to 1.0
        else:  # Too large
            return max(0.5, 1.0 - (area_ratio - 0.30) * 0.5)

    def _compute_angle_score(self, landmarks: Dict) -> float:
        """
        Compute face angle/pose score from landmarks
        Frontal faces score highest

        Args:
            landmarks: Facial landmarks dict with keys like 'left_eye', 'right_eye', etc.

        Returns:
            Angle score (0.0-1.0)
        """
        if not landmarks or len(landmarks) < 2:
            return 0.7  # Default score if landmarks not available

        try:
            # Get eye positions
            left_eye = landmarks.get('left_eye', None)
            right_eye = landmarks.get('right_eye', None)

            if left_eye is None or right_eye is None:
                return 0.7

            # Compute eye angle (should be close to horizontal for frontal faces)
            dx = right_eye[0] - left_eye[0]
            dy = right_eye[1] - left_eye[1]
            angle = abs(np.degrees(np.arctan2(dy, dx)))

            # Normalize angle score (0 degrees = perfect frontal = score 1.0)
            # Angles > 15 degrees indicate head tilt
            if angle <= 5:
                angle_score = 1.0
            elif angle <= 15:
                angle_score = 1.0 - (angle - 5) / 10 * 0.3  # 1.0 to 0.7
            elif angle <= 30:
                angle_score = 0.7 - (angle - 15) / 15 * 0.4  # 0.7 to 0.3
            else:
                angle_score = 0.3

            # Check eye distance (should be reasonable for frontal faces)
            eye_distance = np.sqrt(dx**2 + dy**2)

            # If eyes are too close together, face might be at an angle
            if eye_distance < 30:  # pixels
                angle_score *= 0.7

            return angle_score

        except Exception as e:
            print(f"Error computing angle score: {e}")
            return 0.7

    def _default_quality_scores(self) -> Dict[str, float]:
        """Return default quality scores when computation fails"""
        return {
            'quality_score': 0.5,
            'blur_score': 0.5,
            'size_score': 0.5,
            'angle_score': 0.5,
        }

    def draw_faces(
        self,
        image: np.ndarray,
        detections: List[Dict],
        show_quality: bool = True,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """
        Draw bounding boxes and quality scores on detected faces

        Args:
            image: Image array
            detections: List of detection dicts from detect_faces()
            show_quality: Whether to show quality scores
            color: Box color in BGR format
            thickness: Box line thickness

        Returns:
            Image with drawn boxes and labels
        """
        result_image = image.copy()

        for detection in detections:
            top, right, bottom, left = detection['location']

            # Draw rectangle
            cv2.rectangle(result_image, (left, top), (right, bottom), color, thickness)

            # Draw label with quality score
            if show_quality and 'quality_score' in detection:
                label = f"Q: {detection['quality_score']:.2f}"

                # Color code by quality (green = good, yellow = ok, red = poor)
                if detection['quality_score'] >= 0.7:
                    label_color = (0, 255, 0)  # Green
                elif detection['quality_score'] >= 0.5:
                    label_color = (0, 255, 255)  # Yellow
                else:
                    label_color = (0, 0, 255)  # Red

                # Draw label background
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(
                    result_image,
                    (left, bottom),
                    (left + label_size[0], bottom + label_size[1] + 5),
                    label_color,
                    -1,
                )

                # Draw label text
                cv2.putText(
                    result_image,
                    label,
                    (left, bottom + label_size[1] + 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1,
                )

            # Draw landmarks if available
            if 'landmarks' in detection and detection['landmarks']:
                for landmark_name, (lx, ly) in detection['landmarks'].items():
                    cv2.circle(result_image, (int(lx), int(ly)), 2, (255, 0, 0), -1)

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

    def filter_by_quality(
        self,
        detections: List[Dict],
        min_quality: float = 0.5
    ) -> List[Dict]:
        """
        Filter detections by minimum quality score

        Args:
            detections: List of detection dicts
            min_quality: Minimum quality score (0.0-1.0)

        Returns:
            Filtered list of detections
        """
        return [
            det for det in detections
            if det.get('quality_score', 0.0) >= min_quality
        ]

    def get_best_face(self, detections: List[Dict]) -> Optional[Dict]:
        """
        Get the highest quality face from detections

        Args:
            detections: List of detection dicts

        Returns:
            Detection dict with highest quality score, or None
        """
        if not detections:
            return None

        return max(detections, key=lambda d: d.get('quality_score', 0.0))
