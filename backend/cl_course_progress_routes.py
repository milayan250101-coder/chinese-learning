import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth_routes import get_current_teacher
from backend.auth_models import User
from backend.student_profile_models import Student
from backend.cl_course_progress_models import CLCourseProgress


router = APIRouter(
    prefix="/api/cl-course-progress",
    tags=["CL Course Progress"],
)


class CLCourseProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learned: bool


class CLCourseProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    student_id: int
    course_id: str
    learned: bool
    learned_at: datetime | None
    updated_at: datetime


def get_owned_student(
    db: Session,
    student_id: int,
    teacher_id: int,
):
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.teacher_user_id == teacher_id,
        )
        .first()
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    return student


@router.get(
    "/students/{student_id}",
    response_model=list[CLCourseProgressResponse],
)
def list_student_course_progress(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)

    return (
        db.query(CLCourseProgress)
        .filter(CLCourseProgress.student_id == student_id)
        .order_by(CLCourseProgress.course_id)
        .all()
    )


@router.put(
    "/students/{student_id}/courses/{course_id}",
    response_model=CLCourseProgressResponse,
)
def update_student_course_progress(
    student_id: int,
    course_id: str,
    data: CLCourseProgressUpdate,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)

    if not re.fullmatch(r"CL-\d{2,3}", course_id):
        raise HTTPException(status_code=422, detail="Invalid CL course ID.")

    record = (
        db.query(CLCourseProgress)
        .filter(
            CLCourseProgress.student_id == student_id,
            CLCourseProgress.course_id == course_id,
        )
        .first()
    )

    now = datetime.utcnow()

    if record is None:
        record = CLCourseProgress(
            student_id=student_id,
            course_id=course_id,
            learned=data.learned,
            learned_at=now if data.learned else None,
        )
        db.add(record)
    else:
        record.learned = data.learned
        record.learned_at = now if data.learned else None
        record.updated_at = now

    db.commit()
    db.refresh(record)
    return record
