"""
Database models for the facial recognition system
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
    Model for storing registered persons and their face encodings
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


class Detection(Base):
    """
    Model for storing face detection events from CCTV footage
    """

    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True, index=True)

    # Video information
    video_name = Column(String(500), nullable=False)
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

    # Path to saved detection image
    detection_image_path = Column(String(500))

    # Detection status
    is_unknown = Column(Integer, default=0)  # 1 if person not recognized

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    person = relationship("Person", back_populates="detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, person_id={self.person_id}, video='{self.video_name}', timestamp='{self.timestamp}')>"


# Create all tables
def init_db():
    """Initialize the database by creating all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
