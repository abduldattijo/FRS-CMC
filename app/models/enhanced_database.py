"""
Enhanced database models for cross-video face tracking
Adds support for tracking unknown persons across multiple videos
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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import yaml
import os

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Create database engine
DATABASE_URL = config["database"]["url"]
engine = create_engine(DATABASE_URL, echo=config["database"]["echo"])
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Person(Base):
    """
    Model for storing registered persons (manually added)
    """

    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))
    department = Column(String(100))
    employee_id = Column(String(50), unique=True, index=True)

    # Store face encoding as binary data (pickle format)
    face_encoding = Column(LargeBinary, nullable=False)

    # Path to the registered face image
    image_path = Column(String(500))

    # Metadata
    notes = Column(Text)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    detections = relationship("Detection", back_populates="person", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Person(id={self.id}, name='{self.name}', email='{self.email}')>"


class UnknownPerson(Base):
    """
    Model for tracking unknown persons detected across multiple videos
    These are faces that don't match any registered person but appear multiple times
    """

    __tablename__ = "unknown_persons"

    id = Column(Integer, primary_key=True, index=True)

    # Auto-generated identifier like "Unknown-001", "Unknown-002"
    identifier = Column(String(50), unique=True, nullable=False, index=True)

    # Representative face encoding (average of all sightings or first detection)
    face_encoding = Column(LargeBinary, nullable=False)

    # Path to the first/best detected image
    representative_image_path = Column(String(500))

    # Statistics
    total_detections = Column(Integer, default=1)
    first_seen = Column(DateTime, nullable=False, index=True)
    last_seen = Column(DateTime, nullable=False, index=True)

    # Optional: Can be promoted to a registered person later
    promoted_to_person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    is_active = Column(Integer, default=1)  # Can be deactivated

    # Notes for investigation
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    detections = relationship("Detection", back_populates="unknown_person", cascade="all, delete-orphan")
    promoted_to_person = relationship("Person", foreign_keys=[promoted_to_person_id])

    def __repr__(self):
        return f"<UnknownPerson(id={self.id}, identifier='{self.identifier}', detections={self.total_detections})>"


class Detection(Base):
    """
    Model for storing face detection events from CCTV footage
    Links to either a registered Person OR an UnknownPerson
    """

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)

    # Can link to either a known person OR an unknown person
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True, index=True)
    unknown_person_id = Column(Integer, ForeignKey("unknown_persons.id"), nullable=True, index=True)

    # Video information
    video_name = Column(String(500), nullable=False, index=True)
    video_path = Column(String(500))

    # Detection details
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    confidence = Column(Float)  # Recognition confidence score (0.0 - 1.0)

    # Face location in frame (top, right, bottom, left)
    face_location_top = Column(Integer)
    face_location_right = Column(Integer)
    face_location_bottom = Column(Integer)
    face_location_left = Column(Integer)

    # Store the face encoding for this specific detection
    # Useful for later re-clustering or verification
    face_encoding = Column(LargeBinary, nullable=True)

    # Path to saved detection image
    detection_image_path = Column(String(500))

    # Detection type
    detection_type = Column(String(20), default="unknown")  # "registered", "unknown_tracked", "unknown_new"

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    person = relationship("Person", back_populates="detections")
    unknown_person = relationship("UnknownPerson", back_populates="detections")

    def __repr__(self):
        if self.person_id:
            return f"<Detection(id={self.id}, person_id={self.person_id}, video='{self.video_name}')>"
        elif self.unknown_person_id:
            return f"<Detection(id={self.id}, unknown_person_id={self.unknown_person_id}, video='{self.video_name}')>"
        else:
            return f"<Detection(id={self.id}, type='unmatched', video='{self.video_name}')>"


# Create all tables
def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine)
    print("Enhanced database initialized successfully!")
    print("Tables created:")
    print("  - persons (registered people)")
    print("  - unknown_persons (tracked unknowns)")
    print("  - detections (all face detections)")


if __name__ == "__main__":
    init_db()
