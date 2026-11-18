import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth_routes import get_current_teacher
from backend.auth_models import User
from backend.student_profile_models import (
    Student,
    StudentVocabularyProgress,
    StudentGrammarProgress,
)
from backend.hsk_models import HSKVocabulary, HSKGrammarPoint
from backend.hsk_knowledge_link_models import (
    HSKCourseKnowledgeLink,
    StudentKnowledgeManualEntry,
)


router = APIRouter(
    prefix="/api/hsk/knowledge",
    tags=["HSK Knowledge Links"],
)


class StudentKnowledgeAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_type: Literal["vocabulary", "grammar"]
    knowledge_id: int


class CourseKnowledgeLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_type: Literal["vocabulary", "grammar"]
    knowledge_id: int
    course_series: Literal["CL"]
    course_id: str


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
        raise HTTPException(
            status_code=404,
            detail="Student not found.",
        )

    return student


def get_knowledge(
    db: Session,
    knowledge_type: str,
    knowledge_id: int,
):
    if knowledge_type == "vocabulary":
        item = (
            db.query(HSKVocabulary)
            .filter(HSKVocabulary.number == knowledge_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="HSK vocabulary not found.")

        return {
            "key": f"vocabulary:{item.number}",
            "vocabulary_number": item.number,
            "grammar_point_id": None,
            "syllabus_version": item.syllabus_version or "2025",
            "item": item,
        }

    if knowledge_type == "grammar":
        item = (
            db.query(HSKGrammarPoint)
            .filter(HSKGrammarPoint.id == knowledge_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="HSK grammar point not found.")

        return {
            "key": f"grammar:{item.id}",
            "vocabulary_number": None,
            "grammar_point_id": item.id,
            "syllabus_version": item.syllabus_version or "2025",
            "item": item,
        }

    raise HTTPException(status_code=422, detail="Unsupported knowledge type.")


def validate_cl_course(course_id: str):
    catalog_path = (
        Path(__file__).resolve().parent.parent
        / "curriculum"
        / "CL-course-catalog.json"
    )

    if not catalog_path.is_file():
        raise HTTPException(
            status_code=503,
            detail="CL course catalog is unavailable.",
        )

    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        courses = catalog.get("courses", [])
        valid_ids = {
            str(course.get("course_id"))
            for course in courses
            if isinstance(course, dict) and course.get("course_id")
        }
    except (OSError, json.JSONDecodeError):
        raise HTTPException(
            status_code=503,
            detail="CL course catalog could not be read.",
        )

    if course_id not in valid_ids:
        raise HTTPException(
            status_code=404,
            detail="CL course not found in the official course catalog.",
        )


@router.post("/students/{student_id}/add")
def add_knowledge_to_student(
    student_id: int,
    payload: StudentKnowledgeAddRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)

    knowledge = get_knowledge(
        db,
        payload.knowledge_type,
        payload.knowledge_id,
    )

    key = knowledge["key"]
    version = knowledge["syllabus_version"]
    now = __import__("datetime").datetime.utcnow()

    if payload.knowledge_type == "vocabulary":
        progress = (
            db.query(StudentVocabularyProgress)
            .filter(
                StudentVocabularyProgress.student_id == student_id,
                StudentVocabularyProgress.vocabulary_number
                == knowledge["vocabulary_number"],
            )
            .first()
        )
    else:
        progress = (
            db.query(StudentGrammarProgress)
            .filter(
                StudentGrammarProgress.student_id == student_id,
                StudentGrammarProgress.grammar_point_id
                == knowledge["grammar_point_id"],
                StudentGrammarProgress.syllabus_version == version,
            )
            .first()
        )

    was_already_present = progress is not None

    try:
        if not was_already_present:
            if payload.knowledge_type == "vocabulary":
                progress = StudentVocabularyProgress(
                    student_id=student_id,
                    vocabulary_number=knowledge["vocabulary_number"],
                    syllabus_version=version,
                    learning_status="exposed",
                    review_status="approved",
                    first_seen_at=now,
                    last_seen_at=now,
                    occurrence_count=1,
                )
            else:
                progress = StudentGrammarProgress(
                    student_id=student_id,
                    grammar_point_id=knowledge["grammar_point_id"],
                    syllabus_version=version,
                    learning_status="exposed",
                    review_status="approved",
                    first_seen_at=now,
                    last_seen_at=now,
                    occurrence_count=1,
                )

            db.add(progress)

        # 记录教师手动操作来源。相同学生、知识点和来源只记录一次。
        manual_entry = (
            db.query(StudentKnowledgeManualEntry)
            .filter(
                StudentKnowledgeManualEntry.student_id == student_id,
                StudentKnowledgeManualEntry.knowledge_key == key,
                StudentKnowledgeManualEntry.source_type == "teacher_manual",
            )
            .first()
        )

        manual_source_recorded = manual_entry is not None

        if not manual_entry:
            db.add(
                StudentKnowledgeManualEntry(
                    student_id=student_id,
                    teacher_user_id=teacher.id,
                    knowledge_type=payload.knowledge_type,
                    vocabulary_number=knowledge["vocabulary_number"],
                    grammar_point_id=knowledge["grammar_point_id"],
                    knowledge_key=key,
                    syllabus_version=version,
                    source_type="teacher_manual",
                )
            )
            manual_source_recorded = True

        db.commit()

    except IntegrityError:
        db.rollback()

        # 并发重复请求时，重新检查档案，避免重复写入。
        if payload.knowledge_type == "vocabulary":
            existing = (
                db.query(StudentVocabularyProgress)
                .filter(
                    StudentVocabularyProgress.student_id == student_id,
                    StudentVocabularyProgress.vocabulary_number
                    == knowledge["vocabulary_number"],
                )
                .first()
            )
        else:
            existing = (
                db.query(StudentGrammarProgress)
                .filter(
                    StudentGrammarProgress.student_id == student_id,
                    StudentGrammarProgress.grammar_point_id
                    == knowledge["grammar_point_id"],
                    StudentGrammarProgress.syllabus_version == version,
                )
                .first()
            )

        if existing:
            return {
                "status": "already_present",
                "knowledge_key": key,
                "learning_status": existing.learning_status,
                "message": "该知识点已经在学生档案中。",
            }

        raise HTTPException(
            status_code=409,
            detail="The knowledge record could not be saved because of a data conflict.",
        )

    return {
        "status": "already_present" if was_already_present else "added",
        "knowledge_key": key,
        "learning_status": progress.learning_status if progress else None,
        "manual_source_recorded": manual_source_recorded,
        "message": (
            "该知识点此前已在学生档案中，未重复创建。"
            if was_already_present
            else "已添加到学生知识档案，状态为已接触。"
        ),
    }


@router.post("/courses")
def link_knowledge_to_course(
    payload: CourseKnowledgeLinkRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    course_id = payload.course_id.strip()

    if not course_id:
        raise HTTPException(status_code=422, detail="Course ID cannot be empty.")

    validate_cl_course(course_id)

    knowledge = get_knowledge(
        db,
        payload.knowledge_type,
        payload.knowledge_id,
    )

    existing = (
        db.query(HSKCourseKnowledgeLink)
        .filter(
            HSKCourseKnowledgeLink.teacher_user_id == teacher.id,
            HSKCourseKnowledgeLink.knowledge_key == knowledge["key"],
            HSKCourseKnowledgeLink.course_series == "CL",
            HSKCourseKnowledgeLink.course_id == course_id,
        )
        .first()
    )

    if existing:
        return {
            "status": "already_linked",
            "link_id": existing.id,
            "knowledge_key": knowledge["key"],
            "course_id": course_id,
        }

    link = HSKCourseKnowledgeLink(
        teacher_user_id=teacher.id,
        knowledge_type=payload.knowledge_type,
        vocabulary_number=knowledge["vocabulary_number"],
        grammar_point_id=knowledge["grammar_point_id"],
        knowledge_key=knowledge["key"],
        course_series="CL",
        course_id=course_id,
    )

    db.add(link)

    try:
        db.commit()
        db.refresh(link)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(HSKCourseKnowledgeLink)
            .filter(
                HSKCourseKnowledgeLink.teacher_user_id == teacher.id,
                HSKCourseKnowledgeLink.knowledge_key == knowledge["key"],
                HSKCourseKnowledgeLink.course_series == "CL",
                HSKCourseKnowledgeLink.course_id == course_id,
            )
            .first()
        )
        if existing:
            return {
                "status": "already_linked",
                "link_id": existing.id,
                "knowledge_key": knowledge["key"],
                "course_id": course_id,
            }
        raise HTTPException(status_code=409, detail="Course link could not be saved.")

    return {
        "status": "linked",
        "link_id": link.id,
        "knowledge_key": knowledge["key"],
        "course_series": "CL",
        "course_id": course_id,
    }


@router.get("/{knowledge_type}/{knowledge_id}/courses")
def list_linked_courses(
    knowledge_type: Literal["vocabulary", "grammar"],
    knowledge_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    knowledge = get_knowledge(db, knowledge_type, knowledge_id)

    links = (
        db.query(HSKCourseKnowledgeLink)
        .filter(
            HSKCourseKnowledgeLink.teacher_user_id == teacher.id,
            HSKCourseKnowledgeLink.knowledge_key == knowledge["key"],
        )
        .order_by(HSKCourseKnowledgeLink.created_at)
        .all()
    )

    return {
        "knowledge_key": knowledge["key"],
        "items": [
            {
                "id": link.id,
                "course_series": link.course_series,
                "course_id": link.course_id,
                "created_at": link.created_at,
            }
            for link in links
        ],
    }
