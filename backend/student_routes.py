from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth_routes import get_current_teacher
from backend.auth_models import User
from backend.student_profile_models import Student


router = APIRouter(
    prefix="/api/students",
    tags=["Student Management"]
)


class StudentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=150)
    student_code: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class StudentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=150)
    student_code: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    is_active: bool | None = None


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str
    student_code: str | None
    email: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


def get_owned_student(
    db: Session,
    student_id: int,
    teacher_id: int
):
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.teacher_user_id == teacher_id
        )
        .first()
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    return student


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher)
):
    display_name = data.display_name.strip()

    if not display_name:
        raise HTTPException(
            status_code=422,
            detail="Student name cannot be empty."
        )

    student = Student(
        teacher_user_id=teacher.id,
        display_name=display_name,
        student_code=data.student_code,
        email=data.email,
        notes=data.notes,
        is_active=1
    )

    db.add(student)

    try:
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Student code already exists."
        )

    return student


@router.get("/", response_model=list[StudentResponse])
def list_students(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher)
):
    query = db.query(Student).filter(
        Student.teacher_user_id == teacher.id
    )

    if is_active is not None:
        query = query.filter(Student.is_active == int(is_active))

    return (
        query.order_by(Student.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher)
):
    return get_owned_student(db, student_id, teacher.id)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher)
):
    student = get_owned_student(db, student_id, teacher.id)

    updates = data.model_dump(exclude_unset=True)

    if "display_name" in updates:
        if updates["display_name"] is None:
            raise HTTPException(
                status_code=422,
                detail="Student name cannot be null."
            )

        updates["display_name"] = updates["display_name"].strip()

        if not updates["display_name"]:
            raise HTTPException(
                status_code=422,
                detail="Student name cannot be empty."
            )

    if "is_active" in updates and updates["is_active"] is not None:
        updates["is_active"] = int(updates["is_active"])

    for field, value in updates.items():
        setattr(student, field, value)

    try:
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Student code already exists."
        )

    return student
