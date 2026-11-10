import json
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import LessonPlan  # 注册 lesson_plans 外键关联
from backend.student_profile_models import StudentNote
from backend.student_knowledge.analysis_service import (
    analyze_knowledge_candidates,
)
from backend.student_knowledge.candidate_service import (
    build_knowledge_candidates,
)
from backend.student_knowledge.history_analysis_service import (
    build_history_plan,
    _get_latest_job,
    _read_completed_result,
    _append_prior_evidence,
    _get_or_create_job,
    _save_evidence,
)


def analyze_single_note(
    db: Session,
    student_id: int,
    note_id: int,
    syllabus_version: str = "2025",
    force: bool = False,
) -> dict:
    """
    只分析指定学生的一份课堂资料。

    历史上下文只来自该资料之前已成功分析的资料。
    完全重复的资料复用原始资料结果。
    不自动分析其他资料。
    """

    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == student_id)
        .order_by(StudentNote.created_at, StudentNote.id)
        .all()
    )

    target_note = next(
        (note for note in notes if note.id == note_id),
        None,
    )

    if target_note is None:
        raise ValueError("找不到指定的学生课堂资料。")

    plan = build_history_plan(notes)

    target_plan = next(
        item for item in plan
        if item["note_id"] == note_id
    )

    # 如果当前资料与更早的资料完全重复，直接复用原结果。
    duplicate_of = target_plan["duplicate_of_note_id"]

    if duplicate_of is not None:
        original_job = _get_latest_job(
            db,
            student_id,
            duplicate_of,
        )
        original_result = _read_completed_result(original_job)

        if original_result is None:
            raise ValueError(
                "重复资料对应的原始资料尚未成功分析，"
                "请先分析原始资料。"
            )

        # 原始资料已有成功结果：重复资料复用结果，不再次调用 AI。
        # 只在这次明确的分析 POST 操作中更新重复笔记自身状态。
        target_note.analysis_status = "completed"
        db.commit()

        return {
            "student_id": student_id,
            "note_id": note_id,
            "status": "duplicate",
            "duplicate_of_note_id": duplicate_of,
            "result": original_result,
        }

    # 只收集当前资料之前已经成功完成的历史分析结果。
    prior_knowledge = {
        "vocabulary": [],
        "grammar": [],
    }

    for item in plan:
        if item["note_id"] == note_id:
            break

        # 重复资料不重复加入历史证据。
        if item["duplicate_of_note_id"] is not None:
            continue

        previous_job = _get_latest_job(
            db,
            student_id,
            item["note_id"],
        )
        previous_result = _read_completed_result(previous_job)

        # 尚未成功分析的历史资料不能作为接触证据。
        if previous_result is None:
            continue

        _append_prior_evidence(
            prior_knowledge,
            previous_result,
            item["note_id"],
        )

    job = _get_or_create_job(
        db,
        student_id,
        note_id,
    )

    # 默认复用当前资料已经完成的分析。
    if not force:
        cached_result = _read_completed_result(job)

        if cached_result is not None:
            return {
                "student_id": student_id,
                "note_id": note_id,
                "status": "reused",
                "result": cached_result,
            }

    # 防止同一份资料被并发重复启动。
    if job.status == "running":
        return {
            "student_id": student_id,
            "note_id": note_id,
            "status": "running",
            "message": "这份资料正在分析中。",
        }

    note_text = (target_note.content_text or "").strip()

    if not note_text:
        raise ValueError("课堂资料内容为空。")

    try:
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.completed_at = None
        job.error_message = None
        target_note.analysis_status = "processing"
        db.commit()

        candidates = build_knowledge_candidates(
            db,
            note_text,
            syllabus_version=syllabus_version,
        )

        result = analyze_knowledge_candidates(
            note_text=note_text,
            vocabulary_candidates=candidates["vocabulary"],
            grammar_candidates=candidates["grammar"],
            prior_knowledge=prior_knowledge,
        )

        _save_evidence(
            db,
            student_id,
            note_id,
            result,
            syllabus_version=syllabus_version,
        )

        job.status = "completed"
        job.result_json = json.dumps(
            result,
            ensure_ascii=False,
        )
        job.error_message = None
        job.completed_at = datetime.utcnow()
        target_note.analysis_status = "completed"

        db.commit()

        return {
            "student_id": student_id,
            "note_id": note_id,
            "status": "analyzed",
            "vocabulary_count": len(result["vocabulary"]),
            "grammar_count": len(result["grammar"]),
            "result": result,
        }

    except Exception as exc:
        db.rollback()

        failed_note = db.query(StudentNote).filter(
            StudentNote.id == note_id,
            StudentNote.student_id == student_id,
        ).first()

        failed_job = _get_latest_job(
            db,
            student_id,
            note_id,
        )

        if failed_note is not None:
            failed_note.analysis_status = "failed"

        if failed_job is not None:
            failed_job.status = "failed"
            failed_job.error_message = str(exc)[:1000]
            failed_job.completed_at = datetime.utcnow()

        db.commit()
        raise
