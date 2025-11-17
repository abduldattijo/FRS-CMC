"""
Face recognition functionality for matching detected faces against known faces
"""

import face_recognition
import numpy as np
import pickle
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from .config import settings
from ..models.database import Person


class FaceRecognizer:
    """
    Handles face recognition by comparing face encodings
    """

    def __init__(self, tolerance: float = None):
        """
        Initialize the face recognizer

        Args:
            tolerance: How much distance between faces to consider a match (lower is stricter)
        """
        self.tolerance = tolerance or settings.FACE_TOLERANCE
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []

    def load_known_faces(self, db: Session) -> int:
        """
        Load all known face encodings from the database

        Args:
            db: Database session

        Returns:
            Number of faces loaded
        """
        # Query all active persons
        persons = db.query(Person).filter(Person.is_active == 1).all()

        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []

        for person in persons:
            if person.face_encoding:
                # Deserialize the face encoding
                encoding = pickle.loads(person.face_encoding)
                self.known_face_encodings.append(encoding)
                self.known_face_ids.append(person.id)
                self.known_face_names.append(person.name)

        return len(self.known_face_encodings)

    def recognize_faces(
        self, face_encodings: List[np.ndarray]
    ) -> List[Dict[str, any]]:
        """
        Recognize faces by comparing against known face encodings

        Args:
            face_encodings: List of face encodings to identify

        Returns:
            List of dicts containing person_id, person_name, confidence, is_unknown
        """
        results = []

        for face_encoding in face_encodings:
            result = self._recognize_single_face(face_encoding)
            results.append(result)

        return results

    def _recognize_single_face(self, face_encoding: np.ndarray) -> Dict[str, any]:
        """
        Recognize a single face

        Args:
            face_encoding: Face encoding to identify

        Returns:
            Dict with person_id, person_name, confidence (distance), is_unknown
        """
        if len(self.known_face_encodings) == 0:
            return {
                "person_id": None,
                "person_name": "Unknown",
                "confidence": 0.0,
                "is_unknown": True,
            }

        # Calculate face distances
        face_distances = face_recognition.face_distance(
            self.known_face_encodings, face_encoding
        )

        # Get the best match
        best_match_index = np.argmin(face_distances)
        best_distance = face_distances[best_match_index]

        # Convert distance to confidence (inverse relationship)
        # Distance of 0 = 100% confidence, Distance of 1 = 0% confidence
        confidence = 1.0 - best_distance

        # Check if the match is within tolerance
        if best_distance <= self.tolerance:
            return {
                "person_id": self.known_face_ids[best_match_index],
                "person_name": self.known_face_names[best_match_index],
                "confidence": float(confidence),
                "is_unknown": False,
            }
        else:
            return {
                "person_id": None,
                "person_name": "Unknown",
                "confidence": float(confidence),
                "is_unknown": True,
            }

    def compare_faces(
        self,
        known_encoding: np.ndarray,
        unknown_encoding: np.ndarray,
        tolerance: float = None,
    ) -> Tuple[bool, float]:
        """
        Compare two face encodings

        Args:
            known_encoding: The known face encoding
            unknown_encoding: The face encoding to compare
            tolerance: Optional tolerance override

        Returns:
            Tuple of (is_match, confidence)
        """
        tolerance = tolerance or self.tolerance

        # Calculate distance
        distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]

        # Convert to confidence
        confidence = 1.0 - distance

        # Check if match
        is_match = distance <= tolerance

        return is_match, float(confidence)

    @staticmethod
    def serialize_encoding(encoding: np.ndarray) -> bytes:
        """
        Serialize a face encoding for database storage

        Args:
            encoding: Face encoding array

        Returns:
            Serialized encoding as bytes
        """
        return pickle.dumps(encoding)

    @staticmethod
    def deserialize_encoding(encoding_bytes: bytes) -> np.ndarray:
        """
        Deserialize a face encoding from database

        Args:
            encoding_bytes: Serialized encoding

        Returns:
            Face encoding array
        """
        return pickle.loads(encoding_bytes)

    def get_face_match_stats(self, face_encodings: List[np.ndarray]) -> Dict[str, int]:
        """
        Get statistics about face matches

        Args:
            face_encodings: List of face encodings

        Returns:
            Dict with total_faces, known_faces, unknown_faces
        """
        results = self.recognize_faces(face_encodings)

        known_count = sum(1 for r in results if not r["is_unknown"])
        unknown_count = sum(1 for r in results if r["is_unknown"])

        return {
            "total_faces": len(results),
            "known_faces": known_count,
            "unknown_faces": unknown_count,
        }
