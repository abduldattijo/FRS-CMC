"""
FAISS-based Fast Similarity Search for Cross-Video Matching
Optimized for searching across thousands of face embeddings efficiently
Uses Inner Product search (equivalent to cosine similarity for normalized vectors)
"""

import numpy as np
import faiss
import pickle
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session

from ..models.cross_video_database import VideoFace, CrossVideoMatch


class FAISSMatcher:
    """
    Fast similarity search using FAISS (Facebook AI Similarity Search)
    Enables efficient matching across thousands of face embeddings
    """

    def __init__(
        self,
        embedding_dim: int = 512,
        similarity_threshold: float = 0.62,
        use_gpu: bool = False
    ):
        """
        Initialize FAISS matcher

        Args:
            embedding_dim: Dimension of face embeddings (512 for InsightFace buffalo_l)
            similarity_threshold: Minimum cosine similarity for matches (0.60-0.65 recommended)
            use_gpu: Whether to use GPU acceleration (requires faiss-gpu)
        """
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self.use_gpu = use_gpu

        # FAISS index (will be built when faces are loaded)
        self.index = None

        # Mapping from FAISS index position to VideoFace ID
        self.index_to_face_id = []
        self.index_to_video_id = []

        print(f"✓ FAISSMatcher initialized")
        print(f"  - Embedding dimension: {embedding_dim}D")
        print(f"  - Similarity threshold: {similarity_threshold}")
        print(f"  - GPU acceleration: {'Enabled' if use_gpu else 'Disabled'}")

    def build_index(
        self,
        db: Session,
        video_ids: Optional[List[int]] = None
    ) -> int:
        """
        Build FAISS index from VideoFace embeddings in database

        Args:
            db: Database session
            video_ids: Optional list of video IDs to index (all if None)

        Returns:
            Number of faces indexed
        """
        # Query video faces
        query = db.query(VideoFace)
        if video_ids:
            query = query.filter(VideoFace.video_id.in_(video_ids))

        video_faces = query.all()

        if len(video_faces) == 0:
            print("No video faces found to index")
            return 0

        print(f"\nBuilding FAISS index for {len(video_faces)} faces...")

        # Extract embeddings
        embeddings = []
        face_ids = []
        video_ids_list = []

        for face in video_faces:
            if face.face_encoding:
                embedding = pickle.loads(face.face_encoding)

                # Normalize embedding (required for cosine similarity)
                embedding = embedding / np.linalg.norm(embedding)

                embeddings.append(embedding)
                face_ids.append(face.id)
                video_ids_list.append(face.video_id)

        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Build FAISS index
        # Use Inner Product for normalized vectors (equivalent to cosine similarity)
        self.index = faiss.IndexFlatIP(self.embedding_dim)

        if self.use_gpu:
            try:
                # Move index to GPU
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
                print("✓ FAISS index moved to GPU")
            except Exception as e:
                print(f"GPU acceleration failed, using CPU: {e}")

        # Add vectors to index
        self.index.add(embeddings_array)

        # Store mappings
        self.index_to_face_id = face_ids
        self.index_to_video_id = video_ids_list

        print(f"✓ FAISS index built with {self.index.ntotal} faces")

        return self.index.ntotal

    def find_cross_video_matches(
        self,
        db: Session,
        k_neighbors: int = 50,
        save_matches: bool = True
    ) -> Dict:
        """
        Find cross-video matches using FAISS

        Args:
            db: Database session
            k_neighbors: Number of nearest neighbors to search for each face
            save_matches: Whether to save matches to database

        Returns:
            Dict with matching results
        """
        if self.index is None or self.index.ntotal == 0:
            print("Error: FAISS index not built. Call build_index() first.")
            return {
                "total_faces": 0,
                "total_comparisons": 0,
                "total_matches": 0,
                "matches": []
            }

        print(f"\n{'='*60}")
        print(f"Cross-Video Matching with FAISS")
        print(f"{'='*60}")
        print(f"Total faces in index: {self.index.ntotal}")
        print(f"Searching {k_neighbors} nearest neighbors per face...")
        print(f"{'='*60}\n")

        # Get all embeddings from index
        embeddings_array = self.index.reconstruct_n(0, self.index.ntotal)

        # Search for k nearest neighbors for all faces at once
        # FAISS returns distances (inner products) and indices
        distances, indices = self.index.search(embeddings_array, k_neighbors + 1)  # +1 because first match is self

        matches = []
        total_comparisons = 0

        # Process results
        for source_idx in range(len(embeddings_array)):
            source_face_id = self.index_to_face_id[source_idx]
            source_video_id = self.index_to_video_id[source_idx]

            # Skip first result (self-match)
            for rank in range(1, k_neighbors + 1):
                target_idx = indices[source_idx][rank]
                similarity = float(distances[source_idx][rank])  # Inner product = cosine similarity for normalized vectors

                target_face_id = self.index_to_face_id[target_idx]
                target_video_id = self.index_to_video_id[target_idx]

                total_comparisons += 1

                # Only record cross-video matches
                if source_video_id == target_video_id:
                    continue

                # Only record if above similarity threshold
                if similarity >= self.similarity_threshold:
                    # Avoid duplicate pairs (A->B and B->A)
                    if source_face_id < target_face_id:
                        matches.append({
                            "source_face_id": source_face_id,
                            "target_face_id": target_face_id,
                            "source_video_id": source_video_id,
                            "target_video_id": target_video_id,
                            "similarity_score": similarity,
                        })

        print(f"\n{'='*60}")
        print(f"Matching Complete!")
        print(f"Total comparisons: {total_comparisons:,}")
        print(f"Cross-video matches found: {len(matches)}")
        print(f"{'='*60}\n")

        # Save matches to database
        if save_matches and len(matches) > 0:
            print("Saving matches to database...")

            # Clear existing matches for these faces
            face_ids = self.index_to_face_id
            db.query(CrossVideoMatch).filter(
                CrossVideoMatch.source_face_id.in_(face_ids)
            ).delete(synchronize_session=False)

            # Insert new matches
            for match in matches:
                db_match = CrossVideoMatch(
                    source_face_id=match["source_face_id"],
                    target_face_id=match["target_face_id"],
                    similarity_score=match["similarity_score"],
                    in_same_cluster=0
                )
                db.add(db_match)

            db.commit()
            print(f"✓ Saved {len(matches)} matches to database\n")

        return {
            "total_faces": self.index.ntotal,
            "total_comparisons": total_comparisons,
            "total_matches": len(matches),
            "matches": matches
        }

    def search_similar_faces(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        exclude_video_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Search for similar faces to a query embedding

        Args:
            query_embedding: 512D query face embedding
            k: Number of results to return
            exclude_video_ids: Optional list of video IDs to exclude from results

        Returns:
            List of dicts with face_id, video_id, similarity
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        query_array = query_norm.reshape(1, -1).astype(np.float32)

        # Search
        distances, indices = self.index.search(query_array, k * 2)  # Get more than needed for filtering

        results = []
        for idx, similarity in zip(indices[0], distances[0]):
            if idx == -1:  # FAISS uses -1 for invalid results
                continue

            face_id = self.index_to_face_id[idx]
            video_id = self.index_to_video_id[idx]

            # Filter by video ID if specified
            if exclude_video_ids and video_id in exclude_video_ids:
                continue

            # Filter by threshold
            if similarity < self.similarity_threshold:
                continue

            results.append({
                "face_id": face_id,
                "video_id": video_id,
                "similarity": float(similarity)
            })

            if len(results) >= k:
                break

        return results

    def get_index_stats(self) -> Dict:
        """
        Get statistics about the FAISS index

        Returns:
            Dict with index statistics
        """
        if self.index is None:
            return {
                "index_built": False,
                "total_faces": 0,
                "embedding_dimension": self.embedding_dim,
            }

        # Count faces per video
        video_face_counts = {}
        for video_id in self.index_to_video_id:
            video_face_counts[video_id] = video_face_counts.get(video_id, 0) + 1

        return {
            "index_built": True,
            "total_faces": self.index.ntotal,
            "embedding_dimension": self.embedding_dim,
            "total_videos": len(video_face_counts),
            "faces_per_video": video_face_counts,
            "gpu_enabled": self.use_gpu,
            "similarity_threshold": self.similarity_threshold,
        }

    def save_index(self, filepath: str):
        """
        Save FAISS index to disk

        Args:
            filepath: Path to save index
        """
        if self.index is None:
            print("No index to save")
            return

        try:
            # Save FAISS index
            if self.use_gpu:
                # Convert back to CPU for saving
                cpu_index = faiss.index_gpu_to_cpu(self.index)
                faiss.write_index(cpu_index, filepath)
            else:
                faiss.write_index(self.index, filepath)

            # Save mappings
            mappings = {
                "index_to_face_id": self.index_to_face_id,
                "index_to_video_id": self.index_to_video_id,
                "embedding_dim": self.embedding_dim,
                "similarity_threshold": self.similarity_threshold,
            }

            with open(filepath + ".mappings", "wb") as f:
                pickle.dump(mappings, f)

            print(f"✓ FAISS index saved to {filepath}")

        except Exception as e:
            print(f"Error saving index: {e}")

    def load_index(self, filepath: str):
        """
        Load FAISS index from disk

        Args:
            filepath: Path to load index from
        """
        try:
            # Load FAISS index
            self.index = faiss.read_index(filepath)

            if self.use_gpu:
                # Move to GPU
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, self.index)

            # Load mappings
            with open(filepath + ".mappings", "rb") as f:
                mappings = pickle.load(f)

            self.index_to_face_id = mappings["index_to_face_id"]
            self.index_to_video_id = mappings["index_to_video_id"]
            self.embedding_dim = mappings["embedding_dim"]
            self.similarity_threshold = mappings.get("similarity_threshold", self.similarity_threshold)

            print(f"✓ FAISS index loaded from {filepath}")
            print(f"  - Total faces: {self.index.ntotal}")

        except Exception as e:
            print(f"Error loading index: {e}")

    def clear_index(self):
        """Clear the FAISS index"""
        self.index = None
        self.index_to_face_id = []
        self.index_to_video_id = []
        print("✓ FAISS index cleared")
