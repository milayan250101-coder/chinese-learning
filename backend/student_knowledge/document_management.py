from pathlib import Path
from uuid import uuid4
from datetime import datetime
import json
import os

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, UploadFile
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth_routes import get_current_teacher
from backend.auth_models import User
from backend.database import get_db
from backend.student_routes import get_owned_student
from backend.student_profile_models import (
    StudentNote, StudentNoteFolder, AnalysisJob
)
from backend.student_knowledge.routes import extract_text, MAX_FILE_SIZE
from backend.student_knowledge.history_analysis_service import (
    build_history_plan,
    _get_latest_job,
    _read_completed_result,
)

router = APIRouter(prefix="/api/student-knowledge", tags=["资料管理"])

STORAGE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "private_storage"
    / "student_documents"
)

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}
DOCUMENT_TYPES = {
    "class_notes", "meeting_record", "personalized_article", "other"
}
SOURCE_MODES = {
    "local_file", "pasted_text", "external_link", "google_drive"
}


class MoveDocumentsRequest(BaseModel):
    note_ids: list[int] = Field(min_length=1)
    folder_id: int | None = None


class DeleteOriginalFilesRequest(BaseModel):
    note_ids: list[int] = Field(min_length=1)


def owned_note(db, student_id, note_id):
    note = (
        db.query(StudentNote)
        .filter(
            StudentNote.id == note_id,
            StudentNote.student_id == student_id,
        )
        .first()
    )
    if note is None:
        raise HTTPException(404, "资料不存在。")
    return note


def owned_folder(db, student_id, folder_id):
    if folder_id is None:
        return None
    folder = (
        db.query(StudentNoteFolder)
        .filter(
            StudentNoteFolder.id == folder_id,
            StudentNoteFolder.student_id == student_id,
        )
        .first()
    )
    if folder is None:
        raise HTTPException(404, "目标文件夹不存在或不属于该学生。")
    return folder


def safe_storage_path(value):
    if not value:
        return None
    root = STORAGE_ROOT.resolve()
    path = Path(value).resolve()
    if root not in path.parents:
        raise HTTPException(400, "资料文件路径无效。")
    return path


def restore_staged_file(staged, original):
    """数据库提交失败时，将暂存的原始文件恢复到原位置。"""
    if not staged.exists():
        return
    if original.exists():
        raise FileExistsError(
            f"恢复目标已存在，不能覆盖原文件：{original.name}"
        )
    original.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, original)


def completed_analysis_exists(db, note):
    """验证当前资料或其重复来源资料确实有可读取的成功分析结果。"""
    if note.analysis_status != "completed":
        return False

    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == note.student_id)
        .order_by(StudentNote.created_at, StudentNote.id)
        .all()
    )
    plan = build_history_plan(notes)
    item = next((x for x in plan if x["note_id"] == note.id), None)
    if item is None:
        return False

    # 重复资料必须使用它对应的最早原始资料的分析结果。
    source_note_id = item["duplicate_of_note_id"] or note.id
    source_note = next(
        (x for x in notes if x.id == source_note_id),
        None,
    )
    if source_note is None or source_note.analysis_status != "completed":
        return False

    job = _get_latest_job(db, note.student_id, source_note_id)
    return _read_completed_result(job) is not None


def delete_original_files_for_notes(db, notes):
    """批量暂存原文件，统一提交数据库，再清理暂存文件。"""
    targets = [note for note in notes if note.storage_path]

    # 在改动任何文件前，先验证全部目标资料。
    for note in targets:
        if not completed_analysis_exists(db, note):
            raise HTTPException(
                409,
                f"资料“{note.title}”尚无可验证的成功分析结果，不能删除原始文件。",
            )

    staged_files = []
    timestamp = datetime.utcnow()

    try:
        # 先将所有原件移入同目录暂存区，保留回滚能力。
        for note in targets:
            original = safe_storage_path(note.storage_path)
            if original is None or not original.is_file():
                raise HTTPException(
                    404,
                    f"找不到资料“{note.title}”的原始文件，未提交删除。",
                )

            staged = original.with_name(
                f".pending-delete-{uuid4().hex}"
            )
            os.replace(original, staged)
            staged_files.append((original, staged))

        # 一次事务更新全部资料记录，不删除 StudentNote / KnowledgeEvidence / AnalysisJob。
        for note in targets:
            note.storage_path = None
            note.original_file_deleted_at = timestamp

        db.commit()

    except Exception as original_error:
        db.rollback()
        restore_errors = []

        for original, staged in reversed(staged_files):
            try:
                restore_staged_file(staged, original)
            except OSError as restore_error:
                restore_errors.append(
                    f"{original.name}: {restore_error}"
                )

        if restore_errors:
            raise RuntimeError(
                "数据库操作失败，且部分原始文件恢复失败："
                + "；".join(restore_errors)
            ) from original_error

        raise

    # 数据库提交成功后才真正清理暂存原件。
    for _, staged in staged_files:
        try:
            staged.unlink(missing_ok=True)
        except OSError:
            # 留下暂存文件供后续清理，不回删分析记录或知识证据。
            pass

    return len(targets)


def delete_original_file_for_note(db, note):
    return bool(delete_original_files_for_notes(db, [note]))


@router.get("/students/{student_id}/folders")
def list_folders(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    folders = (
        db.query(StudentNoteFolder)
        .filter(StudentNoteFolder.student_id == student_id)
        .order_by(StudentNoteFolder.sort_order, StudentNoteFolder.id)
        .all()
    )
    return {
        "items": [
            {
                "id": f.id,
                "name": f.name,
                "level_name": f.level_name,
                "sort_order": f.sort_order,
            }
            for f in folders
        ]
    }


@router.post("/students/{student_id}/folders", status_code=201)
def create_folder(
    student_id: int,
    name: str,
    level_name: str | None = None,
    sort_order: int = 0,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    name = name.strip()
    if not name or len(name) > 120:
        raise HTTPException(422, "文件夹名称不能为空，且不能超过120个字符。")

    folder = StudentNoteFolder(
        student_id=student_id,
        name=name,
        level_name=(level_name or "").strip() or None,
        sort_order=sort_order,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name}


@router.patch("/students/{student_id}/folders/{folder_id}")
def rename_folder(
    student_id: int,
    folder_id: int,
    name: str,
    level_name: str | None = None,
    sort_order: int | None = None,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    folder = owned_folder(db, student_id, folder_id)
    name = name.strip()
    if not name or len(name) > 120:
        raise HTTPException(422, "文件夹名称无效。")
    folder.name = name
    if level_name is not None:
        folder.level_name = level_name.strip() or None
    if sort_order is not None:
        folder.sort_order = sort_order
    db.commit()
    return {"status": "updated", "id": folder.id}


@router.delete("/students/{student_id}/folders/{folder_id}")
def delete_folder(
    student_id: int,
    folder_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    folder = owned_folder(db, student_id, folder_id)
    count = (
        db.query(StudentNote)
        .filter(
            StudentNote.student_id == student_id,
            StudentNote.folder_id == folder_id,
        )
        .count()
    )
    if count:
        raise HTTPException(409, "文件夹内还有资料，请先移动资料，再删除文件夹。")
    db.delete(folder)
    db.commit()
    return {"status": "deleted"}


@router.post("/students/{student_id}/documents", status_code=201)
async def create_document(
    student_id: int,
    file: UploadFile | None = File(default=None),
    title: str | None = Form(default=None),
    document_type: str = Form(default="class_notes"),
    source_mode: str = Form(default="local_file"),
    folder_id: int | None = Form(default=None),
    lesson_number: int | None = Form(default=None),
    description: str | None = Form(default=None),
    chinese_text: str | None = Form(default=None),
    pinyin_text: str | None = Form(default=None),
    translation_text: str | None = Form(default=None),
    link_url: str | None = Form(default=None),
    link_provider: str | None = Form(default=None),
    link_title: str | None = Form(default=None),
    external_file_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    student = get_owned_student(db, student_id, teacher.id)

    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(422, "不支持的资料用途类型。")
    if source_mode not in SOURCE_MODES:
        raise HTTPException(422, "不支持的资料来源方式。")
    folder = owned_folder(db, student_id, folder_id)

    filename = None
    file_type = None
    storage_path = None
    extracted = (chinese_text or "").strip()
    clean_url = (link_url or "").strip() or None

    if source_mode == "local_file":
        if file is None:
            raise HTTPException(422, "请选择要上传的文件。")
        filename = (file.filename or "").replace("\\", "/").split("/")[-1]
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(415, "目前支持 TXT、PDF、DOCX 文件。")
        content = await file.read()
        await file.close()
        if not content:
            raise HTTPException(422, "文件内容为空。")
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, "文件不能超过10MB。")
        extracted = extract_text(filename, content)
        file_type = suffix.lstrip(".")
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        target = STORAGE_ROOT / f"{uuid4().hex}{suffix}"
        target.write_bytes(content)
        storage_path = str(target)

    elif source_mode == "pasted_text":
        if not extracted:
            raise HTTPException(422, "请输入要保存的文字内容。")

    elif source_mode == "external_link":
        if not clean_url or not clean_url.startswith(("https://", "http://")):
            raise HTTPException(422, "请输入有效的 http 或 https 白板链接。")

    elif source_mode == "google_drive":
        # 仅保存未来导入所需的引用信息；此处不代表 Drive 已授权或已导入。
        if not clean_url and not external_file_id:
            raise HTTPException(422, "请提供 Google Drive 链接或文件标识。")

    if source_mode in {"local_file", "pasted_text"} and not extracted:
        if storage_path:
            safe_storage_path(storage_path).unlink(missing_ok=True)
        raise HTTPException(422, "无法读取文字内容，请检查文件或输入内容。")

    note = StudentNote(
        student_id=student.id,
        title=(title or link_title or filename or "未命名资料")[:255],
        source_type="upload",
        filename=filename,
        file_type=file_type,
        content_text=extracted or "",
        analysis_status="not_started",
        folder_id=folder.id if folder else None,
        document_type=document_type,
        source_mode=source_mode,
        storage_path=storage_path,
        lesson_number=lesson_number,
        description=description,
        pinyin_text=pinyin_text,
        translation_text=translation_text,
        link_url=clean_url,
        link_provider=(link_provider or "").strip() or None,
        link_title=(link_title or "").strip() or None,
        external_file_id=(external_file_id or "").strip() or None,
    )

    try:
        db.add(note)
        db.commit()
        db.refresh(note)
    except Exception:
        db.rollback()
        if storage_path:
            safe_storage_path(storage_path).unlink(missing_ok=True)
        raise HTTPException(500, "资料保存失败。")

    return {
        "id": note.id,
        "student_id": note.student_id,
        "title": note.title,
        "document_type": note.document_type,
        "source_mode": note.source_mode,
        "folder_id": note.folder_id,
        "analysis_status": note.analysis_status,
        "has_original_file": bool(note.storage_path),
        "link_url": note.link_url,
        "created_at": note.created_at,
    }


@router.get("/students/{student_id}/documents")
def list_documents(
    student_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    notes = (
        db.query(StudentNote)
        .filter(StudentNote.student_id == student_id)
        .order_by(StudentNote.created_at.desc(), StudentNote.id.desc())
        .all()
    )
    return {
        "total": len(notes),
        "items": [
            {
                "id": n.id,
                "student_id": n.student_id,
                "title": n.title,
                "filename": n.filename,
                "file_type": n.file_type,
                "document_type": n.document_type,
                "source_mode": n.source_mode,
                "folder_id": n.folder_id,
                "lesson_number": n.lesson_number,
                "description": n.description,
                "analysis_status": n.analysis_status,
                "created_at": n.created_at,
                "has_original_file": bool(n.storage_path),
                "original_file_deleted_at": n.original_file_deleted_at,
                "link_url": n.link_url,
                "link_provider": n.link_provider,
                "link_title": n.link_title,
                "external_file_id": n.external_file_id,
                "content_text": n.content_text,
                "pinyin_text": n.pinyin_text,
                "translation_text": n.translation_text,
            }
            for n in notes
        ],
    }


@router.post("/students/{student_id}/documents/move")
def move_documents(
    student_id: int,
    payload: MoveDocumentsRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    owned_folder(db, student_id, payload.folder_id)
    ids = list(dict.fromkeys(payload.note_ids))
    notes = (
        db.query(StudentNote)
        .filter(
            StudentNote.student_id == student_id,
            StudentNote.id.in_(ids),
        )
        .all()
    )
    if len(notes) != len(ids):
        raise HTTPException(404, "部分资料不存在或不属于该学生。")
    for note in notes:
        note.folder_id = payload.folder_id
    db.commit()
    return {"status": "moved", "moved_count": len(notes)}


@router.delete("/students/{student_id}/documents/{note_id}")
def refuse_record_deletion(
    student_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    owned_note(db, student_id, note_id)
    raise HTTPException(
        409,
        "为保护学生知识档案，不允许删除整条资料记录。请使用 original-file 接口只删除原始文件。",
    )


@router.delete("/students/{student_id}/documents/{note_id}/original-file")
def delete_one_original_file(
    student_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    note = owned_note(db, student_id, note_id)
    deleted = delete_original_file_for_note(db, note)
    return {
        "status": "original_file_deleted" if deleted else "no_original_file",
        "id": note.id,
        "record_preserved": True,
    }


@router.post("/students/{student_id}/documents/delete-original-files")
def delete_many_original_files(
    student_id: int,
    payload: DeleteOriginalFilesRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    ids = list(dict.fromkeys(payload.note_ids))
    notes = (
        db.query(StudentNote)
        .filter(
            StudentNote.student_id == student_id,
            StudentNote.id.in_(ids),
        )
        .all()
    )
    if len(notes) != len(ids):
        raise HTTPException(404, "部分资料不存在或不属于该学生。")

    deleted_count = delete_original_files_for_notes(db, notes)

    return {
        "status": "original_files_deleted",
        "deleted_count": deleted_count,
        "record_preserved": True,
    }


@router.get("/students/{student_id}/documents/{note_id}/download")
def download_document(
    student_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(get_current_teacher),
):
    get_owned_student(db, student_id, teacher.id)
    note = owned_note(db, student_id, note_id)
    path = safe_storage_path(note.storage_path)
    if path is None or not path.is_file():
        raise HTTPException(404, "没有保存原始文件。")
    return FileResponse(
        path=str(path),
        filename=note.filename or path.name,
        media_type="application/octet-stream",
    )
