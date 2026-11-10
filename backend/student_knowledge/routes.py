from datetime import datetime
from io import BytesIO
from pathlib import PurePath

from docx import Document
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.orm import Session

from backend.auth_routes import get_current_teacher
from backend.auth_models import User
from backend.database import get_db
from backend.student_profile_models import StudentNote
from backend.models import LessonPlan
from backend.student_routes import get_owned_student
from backend.student_knowledge.history_analysis_service import (
    preview_student_history,
    _get_latest_job,
    _read_completed_result,
)
from backend.student_knowledge.single_note_analysis_service import analyze_single_note
from backend.student_knowledge.analysis_service import KnowledgeAnalysisError


router = APIRouter(
    prefix="/api/student-knowledge",
    tags=["Student Knowledge"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def extract_text(filename: str, content: bytes) -> str:
    extension = PurePath(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Only TXT, PDF and DOCX files are supported.",
        )

    try:
        if extension == ".txt":
            text = content.decode("utf-8-sig")

        elif extension == ".pdf":
            reader = PdfReader(BytesIO(content))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )

        else:
            document = Document(BytesIO(content))
            text = "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            )

    except Exception:
        raise HTTPException(
            status_code=422,
            detail="The uploaded document could not be read.",
        )

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the document.",
        )

    return text.strip()


@router.post("/students/{student_id}/notes", status_code=201)
async def upload_student_note(
    student_id: int,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    student = get_owned_student(db, student_id, teacher.id)

    filename = (file.filename or "").replace("\\", "/").split("/")[-1]

    if not filename:
        raise HTTPException(status_code=422, detail="Filename is required.")

    content = await file.read()

    if not content:
        raise HTTPException(status_code=422, detail="The file is empty.")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB.",
        )

    text = extract_text(filename, content)

    note_title = (title or "").strip() or filename

    note = StudentNote(
        student_id=student.id,
        title=note_title[:255],
        source_type="upload",
        filename=filename[:255],
        file_type=PurePath(filename).suffix.lower().lstrip("."),
        content_text=text,
        analysis_status="not_started",
    )

    try:
        db.add(note)
        db.commit()
        db.refresh(note)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The student note could not be saved.",
        )
    finally:
        await file.close()

    return {
        "id": note.id,
        "student_id": note.student_id,
        "title": note.title,
        "filename": note.filename,
        "file_type": note.file_type,
        "analysis_status": note.analysis_status,
        "created_at": note.created_at,
        "message": "Student note uploaded successfully.",
    }


@router.get("/students/{student_id}/notes")
def list_student_notes(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)

    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == student_id)
        .order_by(StudentNote.created_at.desc())
        .all()
    )

    from backend.student_knowledge.history_analysis_service import build_history_plan

    plan_by_id = {
        item["note_id"]: item
        for item in build_history_plan(list(reversed(notes)))
    }

    items = []

    for note in notes:
        plan_item = plan_by_id.get(note.id, {})
        duplicate_of = plan_item.get("duplicate_of_note_id")

        source_status = None
        source_error = None

        if duplicate_of is not None:
            source_job = _get_latest_job(db, student_id, duplicate_of)
            source_result = _read_completed_result(source_job)

            if source_result is not None:
                source_status = "completed"
            elif source_job is not None:
                source_status = source_job.status
            else:
                source_status = "not_started"

            source_error = (
                source_job.error_message
                if source_job is not None
                else None
            )

        items.append({
            "id": note.id,
            "title": note.title,
            "filename": note.filename,
            "file_type": note.file_type,
            "analysis_status": (
                "duplicate" if duplicate_of is not None
                else note.analysis_status
            ),
            "duplicate_of_note_id": duplicate_of,
            "original_analysis_status": source_status,
            "original_error_message": source_error,
            "created_at": note.created_at,
        })

    return {
        "student_id": student_id,
        "total": len(notes),
        "items": items,
    }

# SINGLE_NOTE_ANALYSIS_API

@router.get("/students/{student_id}/history/preview")
def preview_student_knowledge_history(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)

    return preview_student_history(db, student_id)



@router.get("/students/{student_id}/notes/{note_id}/analysis")
def get_student_note_analysis(
    student_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    """只读取已保存的分析结果，不调用 AI、不修改数据库。"""
    get_owned_student(db, student_id, teacher.id)

    note = (
        db.query(StudentNote)
        .filter(
            StudentNote.id == note_id,
            StudentNote.student_id == student_id,
        )
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Student note not found.",
        )

    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == student_id)
        .order_by(StudentNote.created_at, StudentNote.id)
        .all()
    )

    from backend.student_knowledge.history_analysis_service import build_history_plan

    plan_item = next(
        item for item in build_history_plan(notes)
        if item["note_id"] == note_id
    )

    duplicate_of = plan_item["duplicate_of_note_id"]
    source_note_id = duplicate_of or note_id

    job = _get_latest_job(db, student_id, source_note_id)
    result = _read_completed_result(job)

    if duplicate_of is not None:
        status = "duplicate"

        if result is not None:
            original_status = "completed"
        elif job is not None:
            original_status = job.status
        else:
            original_status = "not_started"

        error_message = None
        original_error_message = (
            job.error_message if job is not None else None
        )
    else:
        if result is not None:
            status = "completed"
        elif job is not None and job.status == "running":
            status = "running"
        elif job is not None and job.status == "failed":
            status = "failed"
        else:
            status = "not_started"

        original_status = None
        error_message = job.error_message if job else None
        original_error_message = None

    return {
        "student_id": student_id,
        "note_id": note_id,
        "status": status,
        "note_status": note.analysis_status,
        "job_status": job.status if job else None,
        "error_message": error_message,
        "duplicate_of_note_id": duplicate_of,
        "original_analysis_status": original_status,
        "original_error_message": original_error_message,
        "result": result,
    }

@router.post("/students/{student_id}/notes/{note_id}/analyze")
def analyze_one_student_note(
    student_id: int,
    note_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)

    note = (
        db.query(StudentNote)
        .filter(
            StudentNote.id == note_id,
            StudentNote.student_id == student_id,
        )
        .first()
    )

    if note is None:
        raise HTTPException(
            status_code=404,
            detail="Student note not found.",
        )

    try:
        return analyze_single_note(
            db=db,
            student_id=student_id,
            note_id=note_id,
            force=force,
        )
    except ValueError as exc:
        message = str(exc)

        if "尚未成功分析" in message:
            raise HTTPException(status_code=409, detail=message)

        raise HTTPException(status_code=422, detail=message)
    except KnowledgeAnalysisError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc)[:500],
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="The student note analysis failed.",
        )


@router.post(
    "/students/{student_id}/notes/from-lesson-plan/{lesson_plan_id}",
    status_code=201,
)
def import_lesson_plan_to_student(
    student_id: int,
    lesson_plan_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    """将旧版教案导入指定学生的课堂资料库。"""

    student = get_owned_student(db, student_id, teacher.id)

    lesson = (
        db.query(LessonPlan)
        .filter(
            LessonPlan.id == lesson_plan_id,
            LessonPlan.teacher_user_id == teacher.id,
        )
        .first()
    )

    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="Lesson plan not found.",
        )

    original_text = (lesson.original_text or "").strip()

    if not original_text:
        raise HTTPException(
            status_code=422,
            detail="This lesson plan has no original source text.",
        )

    existing_note = (
        db.query(StudentNote)
        .filter(
            StudentNote.student_id == student.id,
            StudentNote.lesson_plan_id == lesson.id,
        )
        .first()
    )

    if existing_note is not None:
        return {
            "status": "already_imported",
            "student_id": student.id,
            "note_id": existing_note.id,
            "lesson_plan_id": lesson.id,
            "title": existing_note.title,
            "analysis_status": existing_note.analysis_status,
        }

    note = StudentNote(
        student_id=student.id,
        lesson_plan_id=lesson.id,
        title=(lesson.title or "Imported lesson")[:255],
        source_type="lesson_plan",
        filename=None,
        file_type=None,
        content_text=original_text,
        analysis_status="not_started",
    )

    try:
        db.add(note)
        db.commit()
        db.refresh(note)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not import the lesson plan.",
        )

    return {
        "status": "imported",
        "student_id": student.id,
        "note_id": note.id,
        "lesson_plan_id": lesson.id,
        "title": note.title,
        "analysis_status": note.analysis_status,
        "next_step": (
            f"/api/student-knowledge/students/"
            f"{student.id}/notes/{note.id}/analyze"
        ),
    }
