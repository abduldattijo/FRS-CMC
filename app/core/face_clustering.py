"""
Face clustering module for de-duplicating faces within a single video
Uses face encodings and similarity metrics to group the same person's appearances
"""

import numpy as np
from typing import List, Dict, Tuple
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import pickle


class FaceClusterer:
    """
    Clusters face detections within a single video to identify unique individuals
    Same person may appear in multiple frames - this groups them together
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the face clusterer

        Args:
            similarity_threshold: Minimum similarity to group faces (0.0-1.0, higher = stricter)
        """
        self.similarity_threshold = similarity_threshold
        # Convert similarity to distance for DBSCAN (distance = 1 - similarity)
        self.distance_threshold = 1.0 - similarity_threshold

    def cluster_faces(
        self, face_encodings: List[np.ndarray], min_samples: int = 1
    ) -> Tuple[List[int], int]:
        """
        Cluster face encodings to identify unique individuals

        Args:
            face_encodings: List of face encoding vectors
            min_samples: Minimum samples to form a cluster (use 1 for single detections)

        Returns:
            Tuple of (cluster_labels, num_clusters)
            cluster_labels[i] = cluster ID for face i (-1 for noise/outliers)
        """
        if len(face_encodings) == 0:
            return [], 0

        if len(face_encodings) == 1:
            return [0], 1

        # Convert encodings to numpy array
        encodings_array = np.array(face_encodings)

        # Compute cosine distance matrix (1 - cosine_similarity)
        similarity_matrix = cosine_similarity(encodings_array)
        distance_matrix = 1.0 - similarity_matrix

        # Ensure non-negative distances (clip any negative values to 0)
        distance_matrix = np.clip(distance_matrix, 0.0, 2.0)

        # DEBUG: Print similarity statistics
        print(f"\n🔍 Clustering Debug Info:")
        print(f"  Similarity threshold: {self.similarity_threshold}")
        print(f"  Distance threshold (eps): {self.distance_threshold}")
        print(f"  Number of faces: {len(face_encodings)}")

        # Get upper triangle of similarity matrix (avoid diagonal and duplicates)
        triu_indices = np.triu_indices_from(similarity_matrix, k=1)
        similarities = similarity_matrix[triu_indices]

        if len(similarities) > 0:
            print(f"  Similarity scores:")
            print(f"    Min: {similarities.min():.4f}")
            print(f"    Max: {similarities.max():.4f}")
            print(f"    Mean: {similarities.mean():.4f}")
            print(f"    Median: {np.median(similarities):.4f}")
            print(f"  Faces with similarity >= {self.similarity_threshold}: {np.sum(similarities >= self.similarity_threshold)}/{len(similarities)}")
            print(f"  Faces with similarity < 0.80: {np.sum(similarities < 0.80)}/{len(similarities)}")

        # Use DBSCAN for clustering with precomputed distances
        clusterer = DBSCAN(
            eps=self.distance_threshold,
            min_samples=min_samples,
            metric="precomputed"
        )

        cluster_labels = clusterer.fit_predict(distance_matrix)

        # Count unique clusters (excluding noise label -1)
        unique_labels = set(cluster_labels)
        num_clusters = len(unique_labels - {-1})

        print(f"  Result: {num_clusters} unique clusters")
        print(f"  Cluster sizes: {dict(zip(*np.unique(cluster_labels, return_counts=True)))}\n")

        return cluster_labels.tolist(), num_clusters

    def get_representative_encoding(
        self, face_encodings: List[np.ndarray]
    ) -> np.ndarray:
        """
        Get representative face encoding for a cluster (mean of all encodings)

        Args:
            face_encodings: List of face encodings in the cluster

        Returns:
            Mean face encoding vector
        """
        if len(face_encodings) == 0:
            raise ValueError("Cannot compute representative encoding for empty cluster")

        encodings_array = np.array(face_encodings)
        mean_encoding = np.mean(encodings_array, axis=0)

        # Normalize the mean encoding
        norm = np.linalg.norm(mean_encoding)
        if norm > 0:
            mean_encoding = mean_encoding / norm

        return mean_encoding

    def get_best_detection_index(
        self,
        confidences: List[float],
        face_sizes: List[float] = None
    ) -> int:
        """
        Get index of best quality detection in a cluster

        Args:
            confidences: Detection confidence scores
            face_sizes: Optional face bounding box sizes

        Returns:
            Index of best detection
        """
        if len(confidences) == 0:
            raise ValueError("Cannot find best detection in empty list")

        if face_sizes is None:
            # Use highest confidence
            return int(np.argmax(confidences))
        else:
            # Combine confidence and face size (larger faces are typically better quality)
            scores = np.array(confidences) * np.array(face_sizes)
            return int(np.argmax(scores))

    def cluster_detections(
        self, detections: List[Dict]
    ) -> List[Dict]:
        """
        Cluster raw face detections into unique individuals

        Args:
            detections: List of detection dicts with keys:
                - face_encoding: numpy array
                - confidence: float
                - frame_number: int
                - timestamp: datetime
                - face_location: dict with top, right, bottom, left
                - detection_image_path: str
                - (any other metadata)

        Returns:
            List of cluster dicts with keys:
                - cluster_id: int
                - representative_encoding: numpy array
                - representative_detection: dict (best quality detection)
                - all_detections: list of all detections in this cluster
                - appearance_count: int
                - average_confidence: float
                - first_frame: int
                - last_frame: int
                - first_timestamp: datetime
                - last_timestamp: datetime
        """
        if len(detections) == 0:
            return []

        # Extract face encodings
        face_encodings = [d["face_encoding"] for d in detections]

        # Perform clustering
        cluster_labels, num_clusters = self.cluster_faces(face_encodings)

        # Group detections by cluster
        clusters_dict = {}
        for detection, cluster_id in zip(detections, cluster_labels):
            # Handle noise points (cluster_id = -1) by giving each a unique cluster
            if cluster_id == -1:
                cluster_id = len(clusters_dict) + 1000  # Offset to avoid conflicts

            if cluster_id not in clusters_dict:
                clusters_dict[cluster_id] = []

            clusters_dict[cluster_id].append(detection)

        # Build cluster summaries
        cluster_results = []

        for cluster_id, cluster_detections in clusters_dict.items():
            # Get all encodings in cluster
            cluster_encodings = [d["face_encoding"] for d in cluster_detections]

            # Compute representative encoding
            representative_encoding = self.get_representative_encoding(cluster_encodings)

            # Find best quality detection
            confidences = [d["confidence"] for d in cluster_detections]
            face_sizes = []
            for d in cluster_detections:
                loc = d["face_location"]
                width = abs(loc["right"] - loc["left"])
                height = abs(loc["bottom"] - loc["top"])
                face_sizes.append(width * height)

            best_idx = self.get_best_detection_index(confidences, face_sizes)
            representative_detection = cluster_detections[best_idx]

            # Compute statistics
            frame_numbers = [d["frame_number"] for d in cluster_detections]
            timestamps = [d["timestamp"] for d in cluster_detections]

            cluster_summary = {
                "cluster_id": cluster_id,
                "representative_encoding": representative_encoding,
                "representative_detection": representative_detection,
                "all_detections": cluster_detections,
                "appearance_count": len(cluster_detections),
                "average_confidence": float(np.mean(confidences)),
                "best_confidence": float(max(confidences)),
                "first_frame": min(frame_numbers),
                "last_frame": max(frame_numbers),
                "first_timestamp": min(timestamps),
                "last_timestamp": max(timestamps),
            }

            cluster_results.append(cluster_summary)

        return cluster_results

    def compute_similarity(
        self, encoding1: np.ndarray, encoding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two face encodings

        Args:
            encoding1: First face encoding
            encoding2: Second face encoding

        Returns:
            Similarity score (0.0 to 1.0, higher = more similar)
        """
        enc1 = encoding1.reshape(1, -1)
        enc2 = encoding2.reshape(1, -1)

        similarity = cosine_similarity(enc1, enc2)[0][0]
        return float(similarity)

    def is_same_person(
        self, encoding1: np.ndarray, encoding2: np.ndarray, threshold: float = None
    ) -> Tuple[bool, float]:
        """
        Determine if two face encodings belong to the same person

        Args:
            encoding1: First face encoding
            encoding2: Second face encoding
            threshold: Optional custom threshold (uses instance threshold if None)

        Returns:
            Tuple of (is_match, similarity_score)
        """
        threshold = threshold or self.similarity_threshold
        similarity = self.compute_similarity(encoding1, encoding2)

        return similarity >= threshold, similarity
