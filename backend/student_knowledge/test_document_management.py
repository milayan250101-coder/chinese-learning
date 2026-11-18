import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, event, Column, Integer, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend import models, hsk_models, student_profile_models
from backend.student_profile_models import (
    Student,
    StudentNote,
    AnalysisJob,
    KnowledgeEvidence,
)
from backend.student_knowledge import document_management
from backend.student_knowledge.history_analysis_service import JOB_TYPE


# 与现有隔离测试保持一致：只建立测试所需的 users 外键表。
if "users" not in Base.metadata.tables:
    Table(
        "users",
        Base.metadata,
        Column("id", Integer, primary_key=True),
    )


class DocumentManagementTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def disable_foreign_keys_for_isolated_test(
            dbapi_connection, connection_record
        ):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.student = Student(
            teacher_user_id=1,
            display_name="资料管理测试学生",
        )
        self.db.add(self.student)
        self.db.commit()

        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_root = Path(self.temp_dir.name) / "student_documents"
        self.storage_root.mkdir(parents=True)

        self.storage_patcher = patch.object(
            document_management,
            "STORAGE_ROOT",
            self.storage_root,
        )
        self.storage_patcher.start()

        self.result = {
            "vocabulary": [
                {
                    "candidate_id": 1001,
                    "evidence": "喝茶",
                    "confidence": 0.95,
                    "classification": "new_lesson",
                }
            ],
            "grammar": [],
            "observations": [],
        }

    def tearDown(self):
        self.storage_patcher.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def make_note(
        self,
        title="测试课堂资料",
        content="我喜欢喝茶。",
        status="completed",
        created_at=None,
    ):
        note = StudentNote(
            student_id=self.student.id,
            title=title,
            content_text=content,
            analysis_status=status,
            created_at=created_at or datetime.utcnow(),
        )
        self.db.add(note)
        self.db.commit()
        return note

    def add_job(
        self,
        note,
        status="completed",
        result=None,
        created_at=None,
    ):
        job = AnalysisJob(
            student_id=self.student.id,
            note_id=note.id,
            job_type=JOB_TYPE,
            status=status,
            result_json=json.dumps(
                result if result is not None else self.result,
                ensure_ascii=False,
            ),
            created_at=created_at or datetime.utcnow(),
        )
        self.db.add(job)
        self.db.commit()
        return job

    def attach_file(self, note, filename="original.txt"):
        path = self.storage_root / filename
        path.write_text("测试原始资料内容", encoding="utf-8")
        note.storage_path = str(path)
        note.filename = filename
        self.db.commit()
        return path

    def test_successful_delete_preserves_note_evidence_and_job(self):
        note = self.make_note()
        path = self.attach_file(note)
        self.add_job(note)

        evidence = KnowledgeEvidence(
            student_id=self.student.id,
            note_id=note.id,
            vocabulary_number=1001,
            grammar_point_id=None,
            evidence_text="喝茶",
            confidence=0.95,
            classification="new_lesson",
            extraction_method="ai",
        )
        self.db.add(evidence)
        self.db.commit()

        evidence_id = evidence.id
        job_count_before = self.db.query(AnalysisJob).count()

        deleted = document_management.delete_original_file_for_note(
            self.db, note
        )

        self.assertTrue(deleted)
        self.assertFalse(path.exists())

        saved_note = self.db.query(StudentNote).filter_by(id=note.id).one()
        self.assertIsNone(saved_note.storage_path)
        self.assertIsNotNone(saved_note.original_file_deleted_at)
        self.assertEqual(saved_note.content_text, "我喜欢喝茶。")

        self.assertIsNotNone(
            self.db.query(KnowledgeEvidence).filter_by(
                id=evidence_id
            ).first()
        )
        self.assertEqual(
            self.db.query(AnalysisJob).count(),
            job_count_before,
        )

    def test_unanalyzed_note_cannot_delete_original_file(self):
        note = self.make_note(status="not_started")
        path = self.attach_file(note)

        with self.assertRaises(HTTPException) as context:
            document_management.delete_original_file_for_note(
                self.db, note
            )

        self.assertEqual(context.exception.status_code, 409)
        self.assertTrue(path.exists())
        self.db.refresh(note)
        self.assertEqual(note.storage_path, str(path))

    def test_duplicate_note_can_use_original_completed_result(self):
        original = self.make_note(
            title="原始课堂资料",
            content="我喜欢喝茶。",
            created_at=datetime.utcnow(),
        )
        self.add_job(original)

        duplicate = self.make_note(
            title="重复课堂资料",
            content="我喜欢喝茶。",
            created_at=original.created_at + timedelta(minutes=1),
        )
        duplicate_path = self.attach_file(
            duplicate, "duplicate.txt"
        )

        self.assertTrue(
            document_management.completed_analysis_exists(
                self.db, duplicate
            )
        )

        deleted = document_management.delete_original_file_for_note(
            self.db, duplicate
        )

        self.assertTrue(deleted)
        self.assertFalse(duplicate_path.exists())
        self.assertIsNotNone(
            self.db.query(StudentNote).filter_by(
                id=duplicate.id
            ).first()
        )
        self.assertIsNotNone(
            self.db.query(StudentNote).filter_by(
                id=original.id
            ).first()
        )

    def test_latest_failed_job_invalidates_old_completed_result(self):
        note = self.make_note()
        now = datetime.utcnow()

        self.add_job(
            note,
            status="completed",
            created_at=now,
        )
        self.add_job(
            note,
            status="failed",
            result=self.result,
            created_at=now + timedelta(seconds=2),
        )

        self.assertFalse(
            document_management.completed_analysis_exists(
                self.db, note
            )
        )

    def test_batch_prevalidation_prevents_partial_deletion(self):
        valid_note = self.make_note(
            title="有效资料",
            content="我喜欢喝茶。",
        )
        valid_path = self.attach_file(
            valid_note, "valid.txt"
        )
        self.add_job(valid_note)

        invalid_note = self.make_note(
            title="未完成资料",
            content="今天下雨了。",
        )
        invalid_path = self.attach_file(
            invalid_note, "invalid.txt"
        )

        with self.assertRaises(HTTPException):
            document_management.delete_original_files_for_notes(
                self.db,
                [valid_note, invalid_note],
            )

        self.assertTrue(valid_path.exists())
        self.assertTrue(invalid_path.exists())

        self.db.refresh(valid_note)
        self.db.refresh(invalid_note)
        self.assertEqual(valid_note.storage_path, str(valid_path))
        self.assertEqual(invalid_note.storage_path, str(invalid_path))

    def test_database_commit_failure_restores_original_file(self):
        note = self.make_note()
        path = self.attach_file(note)
        self.add_job(note)

        with patch.object(
            self.db,
            "commit",
            side_effect=RuntimeError("模拟数据库提交失败"),
        ):
            with self.assertRaisesRegex(
                RuntimeError, "模拟数据库提交失败"
            ):
                document_management.delete_original_file_for_note(
                    self.db, note
                )

        self.assertTrue(path.exists())
        self.assertEqual(
            list(self.storage_root.glob(".pending-delete-*")),
            [],
        )

        self.db.expire_all()
        saved_note = self.db.query(StudentNote).filter_by(
            id=note.id
        ).one()
        self.assertEqual(saved_note.storage_path, str(path))
        self.assertIsNone(saved_note.original_file_deleted_at)


if __name__ == "__main__":
    unittest.main()
