"""
Improved Face Recognition using InsightFace Buffalo_L model
Generates 512-dimensional embeddings optimized for diverse faces including West African features
Uses cosine similarity with optimized thresholds for darker skin tones
"""

import numpy as np
import pickle
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import cv2

from .config import settings
from ..models.database import Person


class ImprovedFaceRecognizer:
    """
    Advanced face recognition using InsightFace Buffalo_L model
    - 512-dimensional embeddings (vs 128D in dlib)
    - Trained on diverse datasets including African faces
    - Better performance in varying lighting conditions
    - Optimized thresholds for West African features
    """

    def __init__(
        self,
        model_name: str = 'buffalo_l',
        similarity_threshold: float = 0.62,  # Optimized for West African faces
    ):
        """
        Initialize the improved face recognizer

        Args:
            model_name: InsightFace model name ('buffalo_l' recommended for accuracy)
            similarity_threshold: Minimum cosine similarity for match (0.60-0.65 for diverse faces)
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.app = None
        self.known_face_embeddings = []
        self.known_face_ids = []
        self.known_face_names = []

        # Initialize InsightFace model
        self._initialize_model()

        print(f"✓ ImprovedFaceRecognizer initialized with InsightFace {model_name}")
        print(f"  - Embedding dimension: 512D")
        print(f"  - Similarity threshold: {similarity_threshold}")
        print(f"  - Optimized for: West African faces, varying lighting")

    def _initialize_model(self):
        """Initialize InsightFace model"""
        try:
            # Initialize FaceAnalysis with buffalo_l model
            self.app = FaceAnalysis(
                name=self.model_name,
                providers=['CPUExecutionProvider'],  # Use CPU (change to CUDAExecutionProvider for GPU)
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            print(f"✓ InsightFace {self.model_name} model loaded successfully")

        except Exception as e:
            print(f"Error loading InsightFace model: {e}")
            print("Run: python download_models.py to download the model")
            raise

    def get_face_embedding(
        self,
        image: np.ndarray,
        face_location: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[np.ndarray]:
        """
        Get 512D face embedding using InsightFace

        Args:
            image: Image array (BGR format)
            face_location: Optional (top, right, bottom, left) to extract specific face

        Returns:
            512-dimensional embedding array, or None if no face detected
        """
        if face_location is not None:
            # Extract face region
            top, right, bottom, left = face_location
            face_crop = image[top:bottom, left:right]
        else:
            face_crop = image

        if face_crop.size == 0:
            return None

        # InsightFace expects RGB
        if len(face_crop.shape) == 3 and face_crop.shape[2] == 3:
            rgb_image = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = face_crop

        try:
            # Get face embeddings
            faces = self.app.get(rgb_image)

            if len(faces) == 0:
                return None

            # Use the first detected face (or largest if multiple)
            if len(faces) > 1:
                # Sort by bbox area (largest first)
                faces = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

            embedding = faces[0].embedding

            # Normalize embedding (important for cosine similarity)
            embedding = embedding / np.linalg.norm(embedding)

            return embedding

        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None

    def get_multiple_embeddings(
        self,
        image: np.ndarray,
        face_locations: List[Tuple[int, int, int, int]]
    ) -> List[Optional[np.ndarray]]:
        """
        Get embeddings for multiple faces in an image

        Args:
            image: Image array (BGR format)
            face_locations: List of (top, right, bottom, left) face locations

        Returns:
            List of 512D embeddings (None for faces that failed)
        """
        embeddings = []

        for face_location in face_locations:
            embedding = self.get_face_embedding(image, face_location)
            embeddings.append(embedding)

        return embeddings

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two face embeddings

        Args:
            embedding1: First embedding (512D)
            embedding2: Second embedding (512D)

        Returns:
            Similarity score (0.0 to 1.0, higher = more similar)
        """
        # Ensure embeddings are normalized
        emb1 = embedding1 / np.linalg.norm(embedding1)
        emb2 = embedding2 / np.linalg.norm(embedding2)

        # Compute cosine similarity
        similarity = np.dot(emb1, emb2)

        # Clip to [0, 1] range (should already be, but just in case)
        similarity = np.clip(similarity, 0.0, 1.0)

        return float(similarity)

    def load_known_faces(self, db: Session) -> int:
        """
        Load all known face embeddings from the database

        Args:
            db: Database session

        Returns:
            Number of faces loaded
        """
        # Query all active persons
        persons = db.query(Person).filter(Person.is_active == 1).all()

        self.known_face_embeddings = []
        self.known_face_ids = []
        self.known_face_names = []

        for person in persons:
            if person.face_encoding:
                # Deserialize the face embedding
                embedding = pickle.loads(person.face_encoding)

                # Ensure embedding is normalized
                embedding = embedding / np.linalg.norm(embedding)

                self.known_face_embeddings.append(embedding)
                self.known_face_ids.append(person.id)
                self.known_face_names.append(person.name)

        print(f"✓ Loaded {len(self.known_face_embeddings)} known face embeddings")
        return len(self.known_face_embeddings)

    def recognize_face(
        self,
        face_embedding: np.ndarray,
        return_top_k: int = 1
    ) -> List[Dict[str, any]]:
        """
        Recognize a face by comparing against known face embeddings

        Args:
            face_embedding: 512D face embedding to identify
            return_top_k: Number of top matches to return

        Returns:
            List of dicts containing person_id, person_name, similarity, is_match
        """
        if face_embedding is None:
            return [{
                "person_id": None,
                "person_name": "Unknown",
                "similarity": 0.0,
                "is_match": False,
            }]

        if len(self.known_face_embeddings) == 0:
            return [{
                "person_id": None,
                "person_name": "Unknown",
                "similarity": 0.0,
                "is_match": False,
            }]

        # Compute similarities with all known faces
        similarities = []
        for idx, known_embedding in enumerate(self.known_face_embeddings):
            similarity = self.compute_similarity(face_embedding, known_embedding)
            similarities.append({
                "person_id": self.known_face_ids[idx],
                "person_name": self.known_face_names[idx],
                "similarity": similarity,
                "is_match": similarity >= self.similarity_threshold,
            })

        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        # Return top K matches
        top_matches = similarities[:return_top_k]

        # If no matches above threshold, mark as unknown
        if not top_matches[0]['is_match']:
            top_matches[0]['person_name'] = "Unknown"
            top_matches[0]['person_id'] = None

        return top_matches

    def recognize_faces(
        self,
        face_embeddings: List[np.ndarray]
    ) -> List[Dict[str, any]]:
        """
        Recognize multiple faces

        Args:
            face_embeddings: List of 512D face embeddings

        Returns:
            List of dicts containing person_id, person_name, similarity, is_match
        """
        results = []

        for embedding in face_embeddings:
            matches = self.recognize_face(embedding, return_top_k=1)
            results.append(matches[0] if matches else {
                "person_id": None,
                "person_name": "Unknown",
                "similarity": 0.0,
                "is_match": False,
            })

        return results

    @staticmethod
    def serialize_embedding(embedding: np.ndarray) -> bytes:
        """
        Serialize a face embedding for database storage

        Args:
            embedding: Face embedding array (512D)

        Returns:
            Serialized embedding as bytes
        """
        return pickle.dumps(embedding)

    @staticmethod
    def deserialize_embedding(embedding_bytes: bytes) -> np.ndarray:
        """
        Deserialize a face embedding from database

        Args:
            embedding_bytes: Serialized embedding

        Returns:
            Face embedding array (512D)
        """
        return pickle.loads(embedding_bytes)

    def batch_process_images(
        self,
        images: List[np.ndarray],
        face_locations_list: List[List[Tuple[int, int, int, int]]]
    ) -> List[List[Optional[np.ndarray]]]:
        """
        Process multiple images in batch for efficiency

        Args:
            images: List of images
            face_locations_list: List of face location lists (one per image)

        Returns:
            List of embedding lists (one per image)
        """
        all_embeddings = []

        for image, face_locations in zip(images, face_locations_list):
            embeddings = self.get_multiple_embeddings(image, face_locations)
            all_embeddings.append(embeddings)

        return all_embeddings

    def get_embedding_stats(self) -> Dict[str, any]:
        """
        Get statistics about embeddings

        Returns:
            Dict with embedding statistics
        """
        if len(self.known_face_embeddings) == 0:
            return {
                "total_embeddings": 0,
                "embedding_dimension": 512,
                "mean_norm": 0.0,
                "std_norm": 0.0,
            }

        embeddings_array = np.array(self.known_face_embeddings)
        norms = np.linalg.norm(embeddings_array, axis=1)

        return {
            "total_embeddings": len(self.known_face_embeddings),
            "embedding_dimension": embeddings_array.shape[1],
            "mean_norm": float(np.mean(norms)),
            "std_norm": float(np.std(norms)),
            "min_norm": float(np.min(norms)),
            "max_norm": float(np.max(norms)),
        }

    def compare_embeddings(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> Tuple[bool, float]:
        """
        Compare two face embeddings

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Tuple of (is_match, similarity_score)
        """
        similarity = self.compute_similarity(embedding1, embedding2)
        is_match = similarity >= self.similarity_threshold

        return is_match, similarity

    def set_threshold(self, threshold: float):
        """
        Update the similarity threshold

        Args:
            threshold: New threshold (0.0-1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
            print(f"✓ Similarity threshold updated to {threshold}")
        else:
            print(f"✗ Invalid threshold {threshold}. Must be between 0.0 and 1.0")

    def get_match_stats(self, face_embeddings: List[np.ndarray]) -> Dict[str, int]:
        """
        Get statistics about face matches

        Args:
            face_embeddings: List of face embeddings

        Returns:
            Dict with total_faces, matched_faces, unknown_faces
        """
        results = self.recognize_faces(face_embeddings)

        matched_count = sum(1 for r in results if r["is_match"])
        unknown_count = sum(1 for r in results if not r["is_match"])

        return {
            "total_faces": len(results),
            "matched_faces": matched_count,
            "unknown_faces": unknown_count,
        }
