"""
Database models for cross-video identity linking system
For intelligence/surveillance applications where the same person must be tracked across multiple videos
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    LargeBinary,
    Text,
    Table,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import yaml
import os

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Derive a dedicated cross-video database path alongside the main DB
base_db_url = config["database"]["url"]
if base_db_url.startswith("sqlite:///"):
    base_db_path = base_db_url[len("sqlite:///") :]
    base_dir = os.path.dirname(base_db_path)
    os.makedirs(base_dir, exist_ok=True)
    cross_video_db_path = os.path.join(base_dir, "facial_cross_video.db")
    DATABASE_URL = f"sqlite:///{cross_video_db_path}"
else:
    # Fallback: best-effort replace if using a non-sqlite URL format
    DATABASE_URL = base_db_url.replace("recognition", "cross_video")

engine = create_engine(DATABASE_URL, echo=config["database"]["echo"])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Many-to-many relationship table for person clusters
cluster_faces = Table(
    'cluster_faces',
    Base.metadata,
    Column('cluster_id', Integer, ForeignKey('person_clusters.id'), primary_key=True),
    Column('video_face_id', Integer, ForeignKey('video_faces.id'), primary_key=True)
)


class Video(Base):
    """
    Model for tracking uploaded CCTV videos
    """

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False, unique=True, index=True)
    filepath = Column(String(500), nullable=False)

    # Video metadata
    duration_seconds = Column(Float)
    fps = Column(Float)
    total_frames = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)

    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)

    # Statistics
    total_faces_detected = Column(Integer, default=0)
    unique_faces_count = Column(Integer, default=0)

    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    faces = relationship("VideoFace", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, filename='{self.filename}', status='{self.processing_status}')>"


class VideoFace(Base):
    """
    Model for storing unique faces detected in each video
    One entry per unique person per video (de-duplicated within video)
    """

    __tablename__ = "video_faces"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)

    # Auto-generated identifier within the video (e.g., "VideoA_Person_001")
    face_identifier = Column(String(100), nullable=False, index=True)

    # Face encoding (128D or 478D vector depending on model)
    face_encoding = Column(LargeBinary, nullable=False)

    # Representative image (best quality face from all detections)
    representative_image_path = Column(String(500))

    # Statistics for this face within the video
    appearance_count = Column(Integer, default=1)  # How many times detected in this video
    first_frame = Column(Integer)
    last_frame = Column(Integer)
    first_timestamp = Column(DateTime)
    last_timestamp = Column(DateTime)

    # Quality metrics
    average_confidence = Column(Float)  # Average detection confidence
    best_confidence = Column(Float)  # Best detection confidence

    # Clustering assignment (null until cross-video analysis is run)
    cluster_id = Column(Integer, ForeignKey("person_clusters.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="faces")
    cluster = relationship("PersonCluster", secondary=cluster_faces, back_populates="faces")

    # All raw detections for this face
    raw_detections = relationship("RawDetection", back_populates="video_face", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VideoFace(id={self.id}, identifier='{self.face_identifier}', video_id={self.video_id})>"


class RawDetection(Base):
    """
    Model for storing every individual face detection from video frames
    Multiple detections can belong to the same VideoFace (same person in different frames)
    """

    __tablename__ = "raw_detections"

    id = Column(Integer, primary_key=True, index=True)
    video_face_id = Column(Integer, ForeignKey("video_faces.id"), nullable=False, index=True)

    # Frame information
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # Face location in frame (bounding box)
    face_location_top = Column(Integer)
    face_location_right = Column(Integer)
    face_location_bottom = Column(Integer)
    face_location_left = Column(Integer)

    # Detection quality
    confidence = Column(Float)

    # Face encoding for this specific detection
    face_encoding = Column(LargeBinary, nullable=True)

    # Path to saved frame image
    detection_image_path = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    video_face = relationship("VideoFace", back_populates="raw_detections")

    def __repr__(self):
        return f"<RawDetection(id={self.id}, video_face_id={self.video_face_id}, frame={self.frame_number})>"


class PersonCluster(Base):
    """
    Model for grouping faces that belong to the same person across multiple videos
    This is the core of cross-video identity linking
    """

    __tablename__ = "person_clusters"

    id = Column(Integer, primary_key=True, index=True)

    # Auto-generated identifier (e.g., "PERSON_0001", "PERSON_0002")
    cluster_identifier = Column(String(100), unique=True, nullable=False, index=True)

    # Statistics
    total_videos = Column(Integer, default=0)  # How many different videos this person appears in
    total_appearances = Column(Integer, default=0)  # Total detections across all videos

    # Representative encoding (average of all face encodings in cluster)
    representative_encoding = Column(LargeBinary, nullable=True)

    # Best quality image across all videos
    representative_image_path = Column(String(500))

    # Timeline
    first_seen_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    last_seen_video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    first_seen_at = Column(DateTime, index=True)
    last_seen_at = Column(DateTime, index=True)

    # Optional: Manual identification
    identified_name = Column(String(255), nullable=True)
    notes = Column(Text)

    # Status
    is_active = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    faces = relationship("VideoFace", secondary=cluster_faces, back_populates="cluster")

    def __repr__(self):
        return f"<PersonCluster(id={self.id}, identifier='{self.cluster_identifier}', videos={self.total_videos})>"


class CrossVideoMatch(Base):
    """
    Model for storing similarity matches between faces from DIFFERENT videos
    Only stores matches above a certain threshold
    Never stores matches within the same video (A vs A, B vs B)
    """

    __tablename__ = "cross_video_matches"

    id = Column(Integer, primary_key=True, index=True)

    # The two faces being compared (must be from different videos)
    source_face_id = Column(Integer, ForeignKey("video_faces.id"), nullable=False, index=True)
    target_face_id = Column(Integer, ForeignKey("video_faces.id"), nullable=False, index=True)

    # Similarity score (0.0 to 1.0, higher = more similar)
    similarity_score = Column(Float, nullable=False, index=True)

    # Status
    is_confirmed = Column(Integer, default=0)  # Can be manually confirmed by analyst
    is_rejected = Column(Integer, default=0)   # Can be manually rejected

    # Clustering status
    in_same_cluster = Column(Integer, default=0)  # 1 if both faces are in the same PersonCluster

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(255), nullable=True)

    # Relationships
    source_face = relationship("VideoFace", foreign_keys=[source_face_id])
    target_face = relationship("VideoFace", foreign_keys=[target_face_id])

    def __repr__(self):
        return f"<CrossVideoMatch(id={self.id}, similarity={self.similarity_score:.3f}, source={self.source_face_id}, target={self.target_face_id})>"


class AnalysisJob(Base):
    """
    Model for tracking cross-video analysis jobs
    Each job processes a batch of videos and performs cross-video matching
    """

    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job metadata
    job_name = Column(String(255), nullable=False)
    description = Column(Text)

    # Videos included in this analysis
    video_ids = Column(Text)  # Stored as JSON array of video IDs

    # Analysis parameters
    similarity_threshold = Column(Float, default=0.85)  # Minimum similarity to create a match
    clustering_threshold = Column(Float, default=0.90)  # Minimum similarity to group into same cluster

    # Status
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 to 100.0

    # Results
    total_comparisons = Column(Integer, default=0)
    total_matches_found = Column(Integer, default=0)
    total_clusters_created = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AnalysisJob(id={self.id}, name='{self.job_name}', status='{self.status}')>"


# Create all tables
def init_db():
    """Initialize the cross-video analysis database"""
    Base.metadata.create_all(bind=engine)
    print("=" * 60)
    print("Cross-Video Identity Linking Database Initialized!")
    print("=" * 60)
    print("\nTables created:")
    print("  ✓ videos - Track uploaded CCTV videos")
    print("  ✓ video_faces - Unique faces per video (de-duplicated)")
    print("  ✓ raw_detections - All individual face detections")
    print("  ✓ person_clusters - People tracked across videos")
    print("  ✓ cross_video_matches - Face similarity matches between videos")
    print("  ✓ analysis_jobs - Track analysis tasks")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    init_db()
