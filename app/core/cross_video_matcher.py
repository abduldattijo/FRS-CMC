"""
Cross-video face matching module
Compares faces ONLY across different videos to identify the same person appearing in multiple videos
Never compares faces within the same video (A vs A, B vs B)
"""

import numpy as np
from typing import List, Dict, Tuple, Set
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from datetime import datetime
import pickle

from ..models.cross_video_database import (
    VideoFace,
    PersonCluster,
    CrossVideoMatch,
    Video
)


class CrossVideoMatcher:
    """
    Matches faces across different videos to identify the same person
    Core intelligence functionality: "Person X appears in videos A, C, E"
    """

    def __init__(self, similarity_threshold: float = 0.85, clustering_threshold: float = 0.90):
        """
        Initialize the cross-video matcher

        Args:
            similarity_threshold: Minimum similarity to create a match record
            clustering_threshold: Minimum similarity to group into same PersonCluster
        """
        self.similarity_threshold = similarity_threshold
        self.clustering_threshold = clustering_threshold

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

    def find_cross_video_matches(
        self,
        db: Session,
        video_ids: List[int] = None,
        save_matches: bool = True
    ) -> Dict:
        """
        Find face matches across different videos

        Args:
            db: Database session
            video_ids: Optional list of video IDs to analyze (analyzes all if None)
            save_matches: Whether to save matches to database

        Returns:
            Dict with analysis results
        """
        # Get all video faces to compare
        query = db.query(VideoFace)
        if video_ids:
            query = query.filter(VideoFace.video_id.in_(video_ids))

        all_video_faces = query.all()

        if len(all_video_faces) == 0:
            return {
                "total_faces": 0,
                "total_comparisons": 0,
                "total_matches": 0,
                "matches": []
            }

        # Group faces by video
        faces_by_video = {}
        for face in all_video_faces:
            if face.video_id not in faces_by_video:
                faces_by_video[face.video_id] = []
            faces_by_video[face.video_id].append(face)

        video_id_list = list(faces_by_video.keys())

        print(f"\n{'='*60}")
        print(f"Cross-Video Matching Analysis")
        print(f"{'='*60}")
        print(f"Total videos: {len(video_id_list)}")
        print(f"Total faces: {len(all_video_faces)}")
        print(f"{'='*60}\n")

        # Perform cross-video comparisons
        matches = []
        total_comparisons = 0

        # Compare each pair of videos (but not video with itself)
        for i, video_id_a in enumerate(video_id_list):
            for video_id_b in video_id_list[i+1:]:  # Only compare each pair once

                print(f"Comparing Video {video_id_a} vs Video {video_id_b}...")

                faces_a = faces_by_video[video_id_a]
                faces_b = faces_by_video[video_id_b]

                # Compare all faces from video A with all faces from video B
                for face_a in faces_a:
                    encoding_a = pickle.loads(face_a.face_encoding)

                    for face_b in faces_b:
                        encoding_b = pickle.loads(face_b.face_encoding)

                        # Compute similarity
                        similarity = self.compute_similarity(encoding_a, encoding_b)
                        total_comparisons += 1

                        # If above threshold, record the match
                        if similarity >= self.similarity_threshold:
                            match = {
                                "source_face_id": face_a.id,
                                "target_face_id": face_b.id,
                                "source_video_id": face_a.video_id,
                                "target_video_id": face_b.video_id,
                                "source_identifier": face_a.face_identifier,
                                "target_identifier": face_b.face_identifier,
                                "similarity_score": similarity,
                            }
                            matches.append(match)

                            print(f"  ✓ Match found: {face_a.face_identifier} <-> {face_b.face_identifier} (similarity: {similarity:.3f})")

        print(f"\n{'='*60}")
        print(f"Matching Complete!")
        print(f"Total comparisons: {total_comparisons:,}")
        print(f"Matches found: {len(matches)}")
        print(f"{'='*60}\n")

        # Save matches to database
        if save_matches and len(matches) > 0:
            print("Saving matches to database...")

            # Clear existing matches for these videos
            if video_ids:
                db.query(CrossVideoMatch).filter(
                    CrossVideoMatch.source_face_id.in_([f.id for f in all_video_faces])
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
            "total_faces": len(all_video_faces),
            "total_videos": len(video_id_list),
            "total_comparisons": total_comparisons,
            "total_matches": len(matches),
            "matches": matches
        }

    def build_person_clusters(
        self,
        db: Session,
        video_ids: List[int] = None
    ) -> Dict:
        """
        Build PersonClusters by grouping video faces that match across videos

        Args:
            db: Database session
            video_ids: Optional list of video IDs to cluster

        Returns:
            Dict with clustering results
        """
        print(f"\n{'='*60}")
        print(f"Building Person Clusters")
        print(f"{'='*60}\n")

        # Get all matches above clustering threshold
        query = db.query(CrossVideoMatch).filter(
            CrossVideoMatch.similarity_score >= self.clustering_threshold
        )

        if video_ids:
            # Filter to matches involving the specified videos
            video_faces = db.query(VideoFace.id).filter(VideoFace.video_id.in_(video_ids)).all()
            face_ids = [f[0] for f in video_faces]
            query = query.filter(
                (CrossVideoMatch.source_face_id.in_(face_ids)) |
                (CrossVideoMatch.target_face_id.in_(face_ids))
            )

        matches = query.all()

        if len(matches) == 0:
            print("No matches found above clustering threshold.")
            return {
                "total_clusters": 0,
                "total_faces_clustered": 0,
                "clusters": []
            }

        print(f"Found {len(matches)} matches above clustering threshold ({self.clustering_threshold})")

        # Build graph of connected faces using Union-Find algorithm
        face_to_cluster = {}
        cluster_representatives = {}  # cluster_id -> representative face_id

        def find_root(face_id):
            """Find root cluster for a face"""
            if face_id not in face_to_cluster:
                face_to_cluster[face_id] = face_id
                return face_id

            # Path compression
            if face_to_cluster[face_id] != face_id:
                face_to_cluster[face_id] = find_root(face_to_cluster[face_id])

            return face_to_cluster[face_id]

        def union(face_id_1, face_id_2):
            """Merge two faces into same cluster"""
            root1 = find_root(face_id_1)
            root2 = find_root(face_id_2)

            if root1 != root2:
                # Merge smaller cluster into larger one
                face_to_cluster[root2] = root1

        # Process all matches to build clusters
        for match in matches:
            union(match.source_face_id, match.target_face_id)

        # Group faces by their root cluster
        clusters_dict = {}
        for face_id in face_to_cluster.keys():
            root = find_root(face_id)
            if root not in clusters_dict:
                clusters_dict[root] = []
            clusters_dict[root].append(face_id)

        print(f"Created {len(clusters_dict)} person clusters\n")

        # Clear existing clusters for these videos if specified
        if video_ids:
            # Delete old clusters that only contain faces from these videos
            old_clusters = db.query(PersonCluster).all()
            for cluster in old_clusters:
                cluster_video_ids = set(f.video_id for f in cluster.faces)
                if cluster_video_ids.issubset(set(video_ids)):
                    db.delete(cluster)
            db.commit()

        # Create PersonCluster records
        cluster_results = []
        cluster_number = db.query(PersonCluster).count() + 1

        for root_face_id, face_ids in clusters_dict.items():
            # Get all VideoFace objects in this cluster
            video_faces = db.query(VideoFace).filter(VideoFace.id.in_(face_ids)).all()

            # Get unique videos
            video_ids_in_cluster = list(set(f.video_id for f in video_faces))

            # Compute representative encoding (mean of all encodings)
            encodings = [pickle.loads(f.face_encoding) for f in video_faces]
            encodings_array = np.array(encodings)
            mean_encoding = np.mean(encodings_array, axis=0)

            # Normalize
            norm = np.linalg.norm(mean_encoding)
            if norm > 0:
                mean_encoding = mean_encoding / norm

            # Find best representative image (highest confidence)
            best_face = max(video_faces, key=lambda f: f.best_confidence or 0.0)

            # Get timeline
            first_timestamps = [f.first_timestamp for f in video_faces if f.first_timestamp]
            last_timestamps = [f.last_timestamp for f in video_faces if f.last_timestamp]

            # Create PersonCluster
            cluster = PersonCluster(
                cluster_identifier=f"PERSON_{cluster_number:04d}",
                total_videos=len(video_ids_in_cluster),
                total_appearances=sum(f.appearance_count for f in video_faces),
                representative_encoding=pickle.dumps(mean_encoding),
                representative_image_path=best_face.representative_image_path,
                first_seen_video_id=video_ids_in_cluster[0],
                last_seen_video_id=video_ids_in_cluster[-1],
                first_seen_at=min(first_timestamps) if first_timestamps else datetime.utcnow(),
                last_seen_at=max(last_timestamps) if last_timestamps else datetime.utcnow(),
            )

            db.add(cluster)
            db.flush()  # Get the cluster ID

            # Link video faces to this cluster
            for face in video_faces:
                face.cluster_id = cluster.id

            # Update matches to indicate they're in same cluster
            db.query(CrossVideoMatch).filter(
                ((CrossVideoMatch.source_face_id.in_(face_ids)) &
                 (CrossVideoMatch.target_face_id.in_(face_ids)))
            ).update({"in_same_cluster": 1}, synchronize_session=False)

            cluster_results.append({
                "cluster_id": cluster.id,
                "cluster_identifier": cluster.cluster_identifier,
                "total_videos": cluster.total_videos,
                "total_appearances": cluster.total_appearances,
                "video_ids": video_ids_in_cluster,
                "face_ids": face_ids
            })

            print(f"  ✓ {cluster.cluster_identifier}: {cluster.total_appearances} appearances across {cluster.total_videos} videos")

            cluster_number += 1

        db.commit()

        print(f"\n{'='*60}")
        print(f"Clustering Complete!")
        print(f"Total clusters created: {len(cluster_results)}")
        print(f"Total faces clustered: {sum(len(c['face_ids']) for c in cluster_results)}")
        print(f"{'='*60}\n")

        return {
            "total_clusters": len(cluster_results),
            "total_faces_clustered": sum(len(c["face_ids"]) for c in cluster_results),
            "clusters": cluster_results
        }

    def get_cluster_summary(self, db: Session, cluster_id: int) -> Dict:
        """
        Get detailed summary of a person cluster

        Args:
            db: Database session
            cluster_id: PersonCluster ID

        Returns:
            Dict with cluster details
        """
        cluster = db.query(PersonCluster).filter(PersonCluster.id == cluster_id).first()

        if not cluster:
            return None

        # Get all video faces in this cluster
        video_faces = cluster.faces

        # Get videos
        video_ids = list(set(f.video_id for f in video_faces))
        videos = db.query(Video).filter(Video.id.in_(video_ids)).all()

        # Build video appearance map
        video_appearances = []
        for video in videos:
            faces_in_video = [f for f in video_faces if f.video_id == video.id]
            video_appearances.append({
                "video_id": video.id,
                "video_filename": video.filename,
                "appearances": sum(f.appearance_count for f in faces_in_video),
                "first_seen": min(f.first_timestamp for f in faces_in_video if f.first_timestamp),
                "last_seen": max(f.last_timestamp for f in faces_in_video if f.last_timestamp),
            })

        return {
            "cluster_id": cluster.id,
            "cluster_identifier": cluster.cluster_identifier,
            "total_videos": cluster.total_videos,
            "total_appearances": cluster.total_appearances,
            "first_seen": cluster.first_seen_at,
            "last_seen": cluster.last_seen_at,
            "representative_image": cluster.representative_image_path,
            "identified_name": cluster.identified_name,
            "video_appearances": video_appearances
        }
