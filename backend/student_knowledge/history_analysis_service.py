import hashlib
import json
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.student_profile_models import (
    AnalysisJob,
    KnowledgeEvidence,
    StudentNote,
    StudentVocabularyProgress,
    StudentGrammarProgress,
)
from backend.student_knowledge.candidate_service import (
    build_knowledge_candidates,
)
from backend.student_knowledge.analysis_service import (
    analyze_knowledge_candidates,
)


JOB_TYPE = "history_knowledge_analysis"


def _content_hash(content: str) -> str:
    """规范化文本后计算摘要，用于识别重复资料。"""
    normalized = " ".join((content or "").split())
    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def build_history_plan(notes: list[StudentNote]) -> list[dict]:
    """
    按时间顺序建立资料分析计划。

    内容重复的资料保留原记录，但只分析第一次出现的版本。
    """
    ordered_notes = sorted(
        notes,
        key=lambda note: (
            note.created_at or datetime.min,
            note.id,
        ),
    )

    first_seen = {}
    plan = []

    for note in ordered_notes:
        digest = _content_hash(note.content_text or "")
        duplicate_of = first_seen.get(digest)

        if duplicate_of is None:
            first_seen[digest] = note.id

        plan.append({
            "note_id": note.id,
            "title": note.title,
            "created_at": (
                note.created_at.isoformat()
                if note.created_at else None
            ),
            "content_length": len(note.content_text or ""),
            "content_hash": digest,
            "duplicate_of_note_id": duplicate_of,
        })

    return plan


def preview_student_history(
    db: Session,
    student_id: int,
) -> dict:
    """只读预览学生历史资料，不调用 AI，不写入数据库。"""

    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == student_id)
        .order_by(StudentNote.created_at, StudentNote.id)
        .all()
    )

    plan = build_history_plan(notes)

    unique_count = sum(
        1 for item in plan
        if item["duplicate_of_note_id"] is None
    )

    return {
        "student_id": student_id,
        "total_notes": len(plan),
        "unique_notes": unique_count,
        "duplicate_notes": len(plan) - unique_count,
        "items": plan,
    }


def _get_latest_job(
    db: Session,
    student_id: int,
    note_id: int,
):
    return (
        db.query(AnalysisJob)
        .filter(
            AnalysisJob.student_id == student_id,
            AnalysisJob.note_id == note_id,
            AnalysisJob.job_type == JOB_TYPE,
        )
        .order_by(
            AnalysisJob.created_at.desc(),
            AnalysisJob.id.desc(),
        )
        .first()
    )


def _read_completed_result(job):
    """读取已经完成的分析结果；无法解析时返回 None。"""
    if not job or job.status != "completed" or not job.result_json:
        return None

    try:
        result = json.loads(job.result_json)
    except (TypeError, ValueError):
        return None

    if not isinstance(result, dict):
        return None

    if not isinstance(result.get("vocabulary", []), list):
        return None

    if not isinstance(result.get("grammar", []), list):
        return None

    return result


def _append_prior_evidence(
    prior_knowledge: dict,
    result: dict,
    note_id: int,
):
    """把已分析资料中的有效证据加入历史上下文。"""

    for key in ("vocabulary", "grammar"):
        items = result.get(key, [])

        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            candidate_id = item.get("candidate_id")
            evidence = item.get("evidence")

            if candidate_id is None:
                continue

            if not isinstance(evidence, str) or not evidence.strip():
                continue

            prior_knowledge[key].append({
                "candidate_id": candidate_id,
                "evidence": evidence,
                "note_id": note_id,
            })


def _save_evidence(db, student_id, note_id, result, syllabus_version="2025"):
    """保存AI分类证据，并同步学生知识进度。"""
    old = db.query(KnowledgeEvidence).filter_by(
        student_id=student_id, note_id=note_id
    ).all()
    vocab_ids = {x.vocabulary_number for x in old if x.vocabulary_number is not None}
    grammar_ids = {x.grammar_point_id for x in old if x.grammar_point_id is not None}

    db.query(KnowledgeEvidence).filter_by(
        student_id=student_id, note_id=note_id
    ).delete(synchronize_session="fetch")

    allowed = {"new_lesson", "previously_exposed", "uncertain"}
    for item in result.get("vocabulary", []):
        vid = item["candidate_id"]
        vocab_ids.add(vid)
        cls = item.get("classification", "uncertain")
        db.add(KnowledgeEvidence(
            student_id=student_id, note_id=note_id,
            vocabulary_number=vid, grammar_point_id=None,
            evidence_text=item["evidence"], confidence=item.get("confidence"),
            classification=cls if cls in allowed else "uncertain",
            extraction_method="ai",
        ))

    for item in result.get("grammar", []):
        gid = item["candidate_id"]
        grammar_ids.add(gid)
        cls = item.get("classification", "uncertain")
        db.add(KnowledgeEvidence(
            student_id=student_id, note_id=note_id,
            vocabulary_number=None, grammar_point_id=gid,
            evidence_text=item["evidence"], confidence=item.get("confidence"),
            classification=cls if cls in allowed else "uncertain",
            extraction_method="ai",
        ))

    db.flush()

    groups = [
        (vocab_ids, StudentVocabularyProgress, "vocabulary_number", False),
        (grammar_ids, StudentGrammarProgress, "grammar_point_id", True),
    ]
    for ids, model, key, needs_version in groups:
        for item_id in ids:
            filters = {"student_id": student_id, key: item_id}
            if needs_version:
                filters["syllabus_version"] = syllabus_version
            count, first, last = db.query(
                func.count(KnowledgeEvidence.id),
                func.min(KnowledgeEvidence.created_at),
                func.max(KnowledgeEvidence.created_at),
            ).filter(
                KnowledgeEvidence.student_id == student_id,
                getattr(KnowledgeEvidence, key) == item_id,
            ).one()
            progress = db.query(model).filter_by(**filters).first()
            if progress is None and count:
                progress = model(
                    **filters, learning_status="exposed",
                    occurrence_count=count,
                    first_seen_at=first, last_seen_at=last,
                )
                db.add(progress)
            elif progress is not None:
                progress.occurrence_count = count
                if count:
                    progress.first_seen_at = first
                    progress.last_seen_at = last
                    if progress.learning_status == "not_seen":
                        progress.learning_status = "exposed"
                else:
                    progress.first_seen_at = None
                    progress.last_seen_at = None


def _get_or_create_job(
    db: Session,
    student_id: int,
    note_id: int,
):
    job = _get_latest_job(db, student_id, note_id)

    if job is None:
        job = AnalysisJob(
            student_id=student_id,
            note_id=note_id,
            job_type=JOB_TYPE,
            status="queued",
        )
        db.add(job)
        db.flush()

    return job


def analyze_student_history(
    db: Session,
    student_id: int,
    syllabus_version: str = "2025",
    force: bool = False,
) -> dict:
    """
    按时间顺序分析学生的全部课堂资料。

    - 使用此前资料中的知识证据作为历史上下文。
    - 完全重复的资料只分析一次。
    - 已完成的资料默认复用结果。
    - force=True 时重新分析。
    - 不修改学生的 mastered/exposed 掌握状态。
    """

    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == student_id)
        .order_by(StudentNote.created_at, StudentNote.id)
        .all()
    )

    plan = build_history_plan(notes)
    notes_by_id = {note.id: note for note in notes}

    prior_knowledge = {
        "vocabulary": [],
        "grammar": [],
    }

    results_by_note = {}

    summary = {
        "student_id": student_id,
        "total_notes": len(notes),
        "analyzed": 0,
        "reused": 0,
        "duplicates": 0,
        "failed": 0,
        "items": [],
    }

    for plan_item in plan:
        note_id = plan_item["note_id"]
        note = notes_by_id[note_id]
        duplicate_of = plan_item["duplicate_of_note_id"]

        try:
            job = _get_or_create_job(
                db,
                student_id,
                note_id,
            )

            # 重复资料不重复调用 AI。
            if duplicate_of is not None:
                canonical_result = results_by_note.get(duplicate_of)

                if canonical_result is None:
                    canonical_job = _get_latest_job(
                        db,
                        student_id,
                        duplicate_of,
                    )
                    canonical_result = _read_completed_result(
                        canonical_job
                    )

                if canonical_result is None:
                    raise RuntimeError(
                        "重复资料对应的原始资料尚未成功分析。"
                    )

                duplicate_result = {
                    "vocabulary": [],
                    "grammar": [],
                    "observations": [
                        "本资料与历史资料内容重复，"
                        f"沿用资料 ID {duplicate_of} 的分析，"
                        "不重复计数。"
                    ],
                    "duplicate": True,
                    "duplicate_of_note_id": duplicate_of,
                }

                job.status = "completed"
                job.result_json = json.dumps(
                    duplicate_result,
                    ensure_ascii=False,
                )
                job.error_message = None
                job.completed_at = datetime.utcnow()

                note.analysis_status = "completed"

                db.commit()

                summary["duplicates"] += 1
                results_by_note[note_id] = canonical_result

                summary["items"].append({
                    "note_id": note_id,
                    "status": "duplicate",
                    "duplicate_of_note_id": duplicate_of,
                })
                continue

            # 默认复用此前已经成功完成的分析。
            cached_result = None if force else _read_completed_result(job)

            if cached_result is not None:
                results_by_note[note_id] = cached_result

                _append_prior_evidence(
                    prior_knowledge,
                    cached_result,
                    note_id,
                )

                note.analysis_status = "completed"
                db.commit()

                summary["reused"] += 1
                summary["items"].append({
                    "note_id": note_id,
                    "status": "reused",
                })
                continue

            note_text = (note.content_text or "").strip()

            if not note_text:
                raise ValueError("课堂资料内容为空。")

            job.status = "running"
            job.started_at = datetime.utcnow()
            job.completed_at = None
            job.error_message = None

            note.analysis_status = "processing"

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

            note.analysis_status = "completed"

            db.commit()

            results_by_note[note_id] = result

            _append_prior_evidence(
                prior_knowledge,
                result,
                note_id,
            )

            summary["analyzed"] += 1
            summary["items"].append({
                "note_id": note_id,
                "status": "analyzed",
                "vocabulary_count": len(result["vocabulary"]),
                "grammar_count": len(result["grammar"]),
            })

        except Exception as exc:
            db.rollback()

            # 记录失败状态，允许之后重试。
            failed_note = db.query(StudentNote).filter(
                StudentNote.id == note_id,
                StudentNote.student_id == student_id,
            ).first()

            failed_job = _get_or_create_job(
                db,
                student_id,
                note_id,
            )

            if failed_note is not None:
                failed_note.analysis_status = "failed"

            failed_job.status = "failed"
            failed_job.error_message = str(exc)[:1000]
            failed_job.completed_at = datetime.utcnow()

            db.commit()

            summary["failed"] += 1
            summary["items"].append({
                "note_id": note_id,
                "status": "failed",
                "error": str(exc)[:300],
            })

    return summary
