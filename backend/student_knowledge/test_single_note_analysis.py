import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine, event, Column, Integer, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend import models, hsk_models, student_profile_models
from backend.student_profile_models import (
    Student,
    StudentNote,
    AnalysisJob,
)
from backend.student_knowledge.single_note_analysis_service import (
    analyze_single_note,
)
from backend.student_knowledge.history_analysis_service import JOB_TYPE

# 测试专用最小 users 表，仅用于解析外键，不连接正式用户表。
if "users" not in Base.metadata.tables:
    Table(
        "users", Base.metadata,
        Column("id", Integer, primary_key=True),
    )


class SingleNoteAnalysisTests(unittest.TestCase):
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
            display_name="测试学生",
        )
        self.db.add(self.student)
        self.db.flush()

        self.note = StudentNote(
            student_id=self.student.id,
            title="第一课课堂笔记",
            content_text="我喜欢喝茶。",
            created_at=datetime.utcnow(),
        )
        self.db.add(self.note)
        self.db.commit()

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
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @patch(
        "backend.student_knowledge.single_note_analysis_service._save_evidence"
    )
    @patch(
        "backend.student_knowledge.single_note_analysis_service.analyze_knowledge_candidates"
    )
    @patch(
        "backend.student_knowledge.single_note_analysis_service.build_knowledge_candidates"
    )
    def test_successful_analysis_saves_completed_result(
        self, mock_candidates, mock_analyze, mock_save
    ):
        mock_candidates.return_value = {
            "vocabulary": [{"id": 1001}],
            "grammar": [],
        }
        mock_analyze.return_value = self.result

        response = analyze_single_note(
            self.db, self.student.id, self.note.id
        )

        self.assertEqual(response["status"], "analyzed")
        self.assertEqual(response["vocabulary_count"], 1)
        self.assertEqual(mock_save.call_count, 1)

        job = (
            self.db.query(AnalysisJob)
            .filter_by(student_id=self.student.id, note_id=self.note.id)
            .one()
        )
        note = self.db.query(StudentNote).filter_by(id=self.note.id).one()

        self.assertEqual(job.status, "completed")
        self.assertEqual(json.loads(job.result_json), self.result)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(note.analysis_status, "completed")

    @patch(
        "backend.student_knowledge.single_note_analysis_service.analyze_knowledge_candidates"
    )
    @patch(
        "backend.student_knowledge.single_note_analysis_service.build_knowledge_candidates"
    )
    def test_completed_analysis_is_reused_without_ai(
        self, mock_candidates, mock_analyze
    ):
        job = AnalysisJob(
            student_id=self.student.id,
            note_id=self.note.id,
            job_type=JOB_TYPE,
            status="completed",
            result_json=json.dumps(self.result, ensure_ascii=False),
        )
        self.db.add(job)
        self.db.commit()

        response = analyze_single_note(
            self.db, self.student.id, self.note.id
        )

        self.assertEqual(response["status"], "reused")
        self.assertEqual(response["result"], self.result)
        mock_candidates.assert_not_called()
        mock_analyze.assert_not_called()

    @patch(
        "backend.student_knowledge.single_note_analysis_service.analyze_knowledge_candidates"
    )
    @patch(
        "backend.student_knowledge.single_note_analysis_service.build_knowledge_candidates"
    )
    def test_running_job_is_not_started_again(
        self, mock_candidates, mock_analyze
    ):
        job = AnalysisJob(
            student_id=self.student.id,
            note_id=self.note.id,
            job_type=JOB_TYPE,
            status="running",
        )
        self.db.add(job)
        self.db.commit()

        response = analyze_single_note(
            self.db, self.student.id, self.note.id
        )

        self.assertEqual(response["status"], "running")
        mock_candidates.assert_not_called()
        mock_analyze.assert_not_called()

    @patch(
        "backend.student_knowledge.single_note_analysis_service.analyze_knowledge_candidates",
        side_effect=RuntimeError("模拟 AI 分析失败"),
    )
    @patch(
        "backend.student_knowledge.single_note_analysis_service.build_knowledge_candidates"
    )
    def test_analysis_failure_marks_note_and_job_failed(
        self, mock_candidates, mock_analyze
    ):
        mock_candidates.return_value = {
            "vocabulary": [{"id": 1001}],
            "grammar": [],
        }

        with self.assertRaisesRegex(RuntimeError, "模拟 AI 分析失败"):
            analyze_single_note(
                self.db, self.student.id, self.note.id
            )

        job = (
            self.db.query(AnalysisJob)
            .filter_by(student_id=self.student.id, note_id=self.note.id)
            .one()
        )
        note = self.db.query(StudentNote).filter_by(id=self.note.id).one()

        self.assertEqual(job.status, "failed")
        self.assertIn("模拟 AI 分析失败", job.error_message)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(note.analysis_status, "failed")

    @patch(
        "backend.student_knowledge.single_note_analysis_service.analyze_knowledge_candidates"
    )
    @patch(
        "backend.student_knowledge.single_note_analysis_service.build_knowledge_candidates"
    )
    def test_duplicate_note_reuses_original_result(
        self, mock_candidates, mock_analyze
    ):
        original_job = (
            self.db.query(AnalysisJob)
            .filter_by(student_id=self.student.id, note_id=self.note.id)
            .first()
        )
        original_job = AnalysisJob(
            student_id=self.student.id,
            note_id=self.note.id,
            job_type=JOB_TYPE,
            status="completed",
            result_json=json.dumps(self.result, ensure_ascii=False),
        )
        self.db.add(original_job)

        duplicate_note = StudentNote(
            student_id=self.student.id,
            title="重复课堂笔记",
            content_text=self.note.content_text,
            created_at=self.note.created_at + timedelta(minutes=1),
        )
        self.db.add(duplicate_note)
        self.db.commit()

        response = analyze_single_note(
            self.db, self.student.id, duplicate_note.id
        )

        self.assertEqual(response["status"], "duplicate")
        self.assertEqual(response["duplicate_of_note_id"], self.note.id)
        self.assertEqual(response["result"], self.result)

        duplicate_note = (
            self.db.query(StudentNote)
            .filter_by(id=duplicate_note.id)
            .one()
        )
        self.assertEqual(duplicate_note.analysis_status, "completed")
        mock_candidates.assert_not_called()
        mock_analyze.assert_not_called()


if __name__ == "__main__":
    unittest.main()
