"""
API routes for person management (registration, CRUD operations)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
from datetime import datetime

from ...models.enhanced_database import Person
from ...schemas.person import PersonCreate, PersonResponse, PersonUpdate, PersonListResponse
from ...core.config import settings
from ...core import FaceDetector, FaceRecognizer  # Use MediaPipe versions
from ..dependencies import get_db

router = APIRouter(prefix="/persons", tags=["Persons"])

# Initialize face processing components
face_detector = FaceDetector()
face_recognizer = FaceRecognizer()


@router.post("/", response_model=PersonResponse, status_code=201)
async def register_person(
    name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    employee_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Register a new person with their face image

    Args:
        name: Person's full name
        email: Email address
        phone: Phone number
        department: Department name
        employee_id: Employee ID
        notes: Additional notes
        image: Face image file
        db: Database session

    Returns:
        Created person record
    """
    # Validate image file
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Check if employee_id already exists
    if employee_id:
        existing = db.query(Person).filter(Person.employee_id == employee_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID already exists")

    # Check if email already exists
    if email:
        existing = db.query(Person).filter(Person.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

    # Save the image temporarily
    temp_path = f"/tmp/{image.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    try:
        # Read the image
        import cv2
        img = cv2.imread(temp_path)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Detect faces
        face_locations = face_detector.detect_faces(img)

        if len(face_locations) == 0:
            raise HTTPException(
                status_code=400, detail="No face detected in the image"
            )

        if len(face_locations) > 1:
            raise HTTPException(
                status_code=400,
                detail="Multiple faces detected. Please provide an image with only one face",
            )

        # Get face encoding
        face_encodings = face_detector.get_face_encodings(img, face_locations)
        face_encoding = face_encodings[0]

        # Serialize the encoding
        encoding_bytes = face_recognizer.serialize_encoding(face_encoding)

        # Save the image to permanent location
        image_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name.replace(' ', '_')}.jpg"
        image_path = os.path.join(settings.KNOWN_FACES_DIR, image_filename)
        shutil.copy(temp_path, image_path)

        # Create person record
        person = Person(
            name=name,
            email=email,
            phone=phone,
            department=department,
            employee_id=employee_id,
            notes=notes,
            face_encoding=encoding_bytes,
            image_path=image_path,
            is_active=1,
        )

        db.add(person)
        db.commit()
        db.refresh(person)

        return person

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/", response_model=PersonListResponse)
def get_all_persons(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    Get list of all registered persons

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Return only active persons
        db: Database session

    Returns:
        List of persons
    """
    query = db.query(Person)

    if active_only:
        query = query.filter(Person.is_active == 1)

    total = query.count()
    persons = query.offset(skip).limit(limit).all()

    return {"total": total, "persons": persons}


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: int, db: Session = Depends(get_db)):
    """
    Get a specific person by ID

    Args:
        person_id: Person ID
        db: Database session

    Returns:
        Person record
    """
    person = db.query(Person).filter(Person.id == person_id).first()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    return person


@router.put("/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: int, person_update: PersonUpdate, db: Session = Depends(get_db)
):
    """
    Update a person's information (except face encoding)

    Args:
        person_id: Person ID
        person_update: Updated person data
        db: Database session

    Returns:
        Updated person record
    """
    person = db.query(Person).filter(Person.id == person_id).first()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Update fields
    update_data = person_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "is_active":
            setattr(person, field, 1 if value else 0)
        else:
            setattr(person, field, value)

    person.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(person)

    return person


@router.delete("/{person_id}", status_code=204)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    """
    Delete a person (soft delete by setting is_active = 0)

    Args:
        person_id: Person ID
        db: Database session
    """
    person = db.query(Person).filter(Person.id == person_id).first()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Soft delete
    person.is_active = 0
    person.updated_at = datetime.utcnow()

    db.commit()

    return None


@router.post("/{person_id}/reactivate", response_model=PersonResponse)
def reactivate_person(person_id: int, db: Session = Depends(get_db)):
    """
    Reactivate a deactivated person

    Args:
        person_id: Person ID
        db: Database session

    Returns:
        Reactivated person record
    """
    person = db.query(Person).filter(Person.id == person_id).first()

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    person.is_active = 1
    person.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(person)

    return person
