"""
Enhanced face recognition that tracks unknown persons across multiple videos
"""

import numpy as np
import pickle
from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from .config import settings
from ..models.enhanced_database import Person, UnknownPerson, Detection


class EnhancedFaceRecognizer:
    """
    Advanced face recognizer that matches against:
    1. Registered persons (manually added)
    2. Unknown persons (detected in previous videos)
    """

    def __init__(self, tolerance: float = None, unknown_tolerance: float = None):
        """
        Initialize the enhanced face recognizer

        Args:
            tolerance: Similarity threshold for registered persons (0.0-1.0)
            unknown_tolerance: Similarity threshold for unknown persons (usually lower)
        """
        self.tolerance = tolerance or 0.85  # Stricter for registered persons
        self.unknown_tolerance = unknown_tolerance or 0.80  # Slightly looser for unknowns

        # Registered persons
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []

        # Unknown persons (tracked across videos)
        self.unknown_face_encodings = []
        self.unknown_face_ids = []
        self.unknown_face_identifiers = []

    def load_all_known_faces(self, db: Session) -> Dict[str, int]:
        """
        Load both registered persons AND unknown persons from database

        Args:
            db: Database session

        Returns:
            Dict with counts: {'registered': X, 'unknown_tracked': Y}
        """
        # Load registered persons
        registered_count = self._load_registered_persons(db)

        # Load unknown persons from previous videos
        unknown_count = self._load_unknown_persons(db)

        return {
            'registered': registered_count,
            'unknown_tracked': unknown_count,
            'total': registered_count + unknown_count
        }

    def _load_registered_persons(self, db: Session) -> int:
        """Load registered persons from database"""
        persons = db.query(Person).filter(Person.is_active == 1).all()

        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []

        for person in persons:
            if person.face_encoding:
                encoding = pickle.loads(person.face_encoding)
                self.known_face_encodings.append(encoding)
                self.known_face_ids.append(person.id)
                self.known_face_names.append(person.name)

        return len(self.known_face_encodings)

    def _load_unknown_persons(self, db: Session) -> int:
        """Load unknown persons (tracked across videos) from database"""
        unknown_persons = db.query(UnknownPerson).filter(
            UnknownPerson.is_active == 1,
            UnknownPerson.promoted_to_person_id.is_(None)  # Not yet promoted
        ).all()

        self.unknown_face_encodings = []
        self.unknown_face_ids = []
        self.unknown_face_identifiers = []

        for unknown in unknown_persons:
            if unknown.face_encoding:
                encoding = pickle.loads(unknown.face_encoding)
                self.unknown_face_encodings.append(encoding)
                self.unknown_face_ids.append(unknown.id)
                self.unknown_face_identifiers.append(unknown.identifier)

        return len(self.unknown_face_encodings)

    def recognize_faces(
        self, face_encodings: List[np.ndarray], db: Session = None
    ) -> List[Dict[str, any]]:
        """
        Recognize faces by comparing against:
        1. Registered persons (highest priority)
        2. Unknown persons from previous videos
        3. New unknown person

        Args:
            face_encodings: List of face encodings to identify
            db: Database session (optional, for saving new unknowns)

        Returns:
            List of dicts with recognition results
        """
        results = []

        for face_encoding in face_encodings:
            result = self._recognize_single_face(face_encoding, db)
            results.append(result)

        return results

    def _recognize_single_face(self, face_encoding: np.ndarray, db: Session = None) -> Dict[str, any]:
        """
        Recognize a single face with priority:
        1. Check registered persons first
        2. Check unknown persons from previous videos
        3. Mark as new unknown if no match
        """

        # STEP 1: Try to match against REGISTERED PERSONS (highest priority)
        registered_match = self._match_against_registered(face_encoding)
        if registered_match:
            return registered_match

        # STEP 2: Try to match against UNKNOWN PERSONS (from previous videos)
        unknown_match = self._match_against_unknowns(face_encoding)
        if unknown_match:
            return unknown_match

        # STEP 3: This is a NEW UNKNOWN person
        return {
            "person_id": None,
            "person_name": None,
            "unknown_person_id": None,
            "unknown_identifier": None,
            "confidence": 0.0,
            "detection_type": "unknown_new",  # NEW unknown person
            "is_new_unknown": True,
            "encoding": face_encoding  # Save for creating new unknown person
        }

    def _match_against_registered(self, face_encoding: np.ndarray) -> Optional[Dict[str, any]]:
        """Match against registered persons"""
        if len(self.known_face_encodings) == 0:
            return None

        # Calculate similarities
        similarities = []
        for known_encoding in self.known_face_encodings:
            enc1 = face_encoding.reshape(1, -1)
            enc2 = known_encoding.reshape(1, -1)
            similarity = cosine_similarity(enc1, enc2)[0][0]
            similarities.append(similarity)

        similarities = np.array(similarities)
        best_match_index = np.argmax(similarities)
        best_similarity = similarities[best_match_index]

        # Check if match meets threshold
        if best_similarity >= self.tolerance:
            return {
                "person_id": self.known_face_ids[best_match_index],
                "person_name": self.known_face_names[best_match_index],
                "unknown_person_id": None,
                "unknown_identifier": None,
                "confidence": float(best_similarity),
                "detection_type": "registered",
                "is_new_unknown": False
            }

        return None

    def _match_against_unknowns(self, face_encoding: np.ndarray) -> Optional[Dict[str, any]]:
        """Match against unknown persons from previous videos"""
        if len(self.unknown_face_encodings) == 0:
            return None

        # Calculate similarities
        similarities = []
        for unknown_encoding in self.unknown_face_encodings:
            enc1 = face_encoding.reshape(1, -1)
            enc2 = unknown_encoding.reshape(1, -1)
            similarity = cosine_similarity(enc1, enc2)[0][0]
            similarities.append(similarity)

        similarities = np.array(similarities)
        best_match_index = np.argmax(similarities)
        best_similarity = similarities[best_match_index]

        # Check if match meets threshold (slightly lower than registered)
        if best_similarity >= self.unknown_tolerance:
            return {
                "person_id": None,
                "person_name": None,
                "unknown_person_id": self.unknown_face_ids[best_match_index],
                "unknown_identifier": self.unknown_face_identifiers[best_match_index],
                "confidence": float(best_similarity),
                "detection_type": "unknown_tracked",  # Tracked unknown
                "is_new_unknown": False
            }

        return None

    def create_unknown_person(
        self, face_encoding: np.ndarray, db: Session, first_detection_info: Dict = None
    ) -> UnknownPerson:
        """
        Create a new unknown person entry in database

        Args:
            face_encoding: Face encoding to save
            db: Database session
            first_detection_info: Info about first detection (optional)

        Returns:
            Created UnknownPerson object
        """
        # Generate unique identifier
        count = db.query(UnknownPerson).count()
        identifier = f"Unknown-{count + 1:04d}"  # e.g., Unknown-0001

        # Serialize encoding
        encoding_bytes = pickle.dumps(face_encoding)

        # Create unknown person
        unknown_person = UnknownPerson(
            identifier=identifier,
            face_encoding=encoding_bytes,
            representative_image_path=first_detection_info.get('image_path') if first_detection_info else None,
            total_detections=1,
            first_seen=first_detection_info.get('timestamp', datetime.utcnow()) if first_detection_info else datetime.utcnow(),
            last_seen=first_detection_info.get('timestamp', datetime.utcnow()) if first_detection_info else datetime.utcnow(),
            is_active=1
        )

        db.add(unknown_person)
        db.commit()
        db.refresh(unknown_person)

        # DO NOT add to in-memory cache during video processing
        # This ensures we only match against PREVIOUS videos, not current video
        # (Clustering of duplicates within video happens at the end)

        return unknown_person

    def update_unknown_person_sighting(
        self, unknown_person_id: int, db: Session, timestamp: datetime = None
    ):
        """
        Update unknown person's sighting count and last seen time

        Args:
            unknown_person_id: ID of unknown person
            db: Database session
            timestamp: Detection timestamp
        """
        unknown = db.query(UnknownPerson).filter(UnknownPerson.id == unknown_person_id).first()
        if unknown:
            unknown.total_detections += 1
            unknown.last_seen = timestamp or datetime.utcnow()
            unknown.updated_at = datetime.utcnow()
            db.commit()

    def cluster_and_merge_duplicates(
        self, unknown_person_ids: List[int], db: Session
    ) -> Dict[str, any]:
        """
        Cluster unknown persons created from the same video and merge duplicates.
        This ensures same person appearing multiple times = 1 database entry.

        Args:
            unknown_person_ids: List of unknown person IDs created from current video
            db: Database session

        Returns:
            Dict with clustering statistics
        """
        if len(unknown_person_ids) <= 1:
            return {
                "total_input": len(unknown_person_ids),
                "unique_after_clustering": len(unknown_person_ids),
                "duplicates_merged": 0
            }

        # Load all unknown persons
        unknowns = db.query(UnknownPerson).filter(
            UnknownPerson.id.in_(unknown_person_ids)
        ).all()

        # Extract encodings
        encodings = []
        unknown_map = {}
        for unknown in unknowns:
            if unknown.face_encoding:
                encoding = pickle.loads(unknown.face_encoding)
                encodings.append(encoding)
                unknown_map[len(encodings) - 1] = unknown

        if len(encodings) <= 1:
            return {
                "total_input": len(unknown_person_ids),
                "unique_after_clustering": len(encodings),
                "duplicates_merged": 0
            }

        # Cluster similar faces
        clusters = []
        used = set()

        for i in range(len(encodings)):
            if i in used:
                continue

            # Start new cluster
            cluster = [i]
            used.add(i)

            # Find similar faces
            for j in range(i + 1, len(encodings)):
                if j in used:
                    continue

                # Calculate similarity
                enc1 = encodings[i].reshape(1, -1)
                enc2 = encodings[j].reshape(1, -1)
                similarity = cosine_similarity(enc1, enc2)[0][0]

                # If similar enough, add to cluster
                if similarity >= self.unknown_tolerance:
                    cluster.append(j)
                    used.add(j)

            clusters.append(cluster)

        # Merge duplicates: Keep first of each cluster, merge others into it
        duplicates_merged = 0
        from ..models.enhanced_database import Detection

        for cluster in clusters:
            if len(cluster) <= 1:
                continue

            # Keep the first one, merge others into it
            primary_idx = cluster[0]
            primary_unknown = unknown_map[primary_idx]

            for idx in cluster[1:]:
                duplicate_unknown = unknown_map[idx]

                # Transfer all detections from duplicate to primary
                db.query(Detection).filter(
                    Detection.unknown_person_id == duplicate_unknown.id
                ).update({
                    "unknown_person_id": primary_unknown.id
                })

                # Update primary's total count
                primary_unknown.total_detections += duplicate_unknown.total_detections

                # Update timestamps if needed
                if duplicate_unknown.first_seen < primary_unknown.first_seen:
                    primary_unknown.first_seen = duplicate_unknown.first_seen
                if duplicate_unknown.last_seen > primary_unknown.last_seen:
                    primary_unknown.last_seen = duplicate_unknown.last_seen

                # Mark duplicate as inactive (merged)
                duplicate_unknown.is_active = 0
                duplicate_unknown.notes = f"Merged into {primary_unknown.identifier}"

                duplicates_merged += 1

        db.commit()

        return {
            "total_input": len(unknown_person_ids),
            "unique_after_clustering": len(clusters),
            "duplicates_merged": duplicates_merged
        }

    @staticmethod
    def serialize_encoding(encoding: np.ndarray) -> bytes:
        """Serialize a face encoding for database storage"""
        return pickle.dumps(encoding)

    @staticmethod
    def deserialize_encoding(encoding_bytes: bytes) -> np.ndarray:
        """Deserialize a face encoding from database"""
        return pickle.loads(encoding_bytes)
