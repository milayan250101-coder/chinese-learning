import unittest
from datetime import datetime
from sqlalchemy import create_engine, event, Column, Integer, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend import models, hsk_models, student_profile_models
from backend.student_profile_models import (
    Student,
    StudentNote,
    KnowledgeEvidence,
    StudentVocabularyProgress,
    StudentGrammarProgress,
)
from backend.hsk_models import HSKVocabulary, HSKGrammarPoint
from backend.student_knowledge.history_analysis_service import _save_evidence


if "users" not in Base.metadata.tables:
    Table(
        "users",
        Base.metadata,
        Column("id", Integer, primary_key=True),
    )


class EvidenceSyncTests(unittest.TestCase):

    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def disable_foreign_keys(connection, record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.close()

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.student = Student(
            teacher_user_id=1,
            display_name="证据同步测试学生",
        )
        self.db.add(self.student)
        self.db.flush()

        self.note1 = StudentNote(
            student_id=self.student.id,
            title="第一课",
            content_text="我喜欢喝茶。",
            created_at=datetime(2026, 1, 1, 10, 0),
        )
        self.note2 = StudentNote(
            student_id=self.student.id,
            title="第二课",
            content_text="我也喜欢喝茶。",
            created_at=datetime(2026, 1, 2, 10, 0),
        )
        self.db.add_all([self.note1, self.note2])

        self.vocab = HSKVocabulary(
            number=900001,
            level="HSK 1",
            simplified="喜欢",
            traditional="喜歡",
            pinyin="xǐhuan",
            english="to like",
            part_of_speech="verb",
            syllabus_version="2025",
            source_repo="test",
            source_file="test.json",
        )

        self.grammar = HSKGrammarPoint(
            level="HSK 1",
            category="sentence",
            category_name="句型",
            subcategory="基础句型",
            content="主谓宾结构",
            syllabus_version="2025",
            source_repo="test",
            source_file="test.json",
            source_url="https://example.com/test",
            source_index=1,
        )

        self.db.add_all([self.vocab, self.grammar])
        self.db.commit()

        self.result = {
            "vocabulary": [
                {
                    "candidate_id": self.vocab.number,
                    "evidence": "喜欢喝茶",
                    "confidence": 0.95,
                    "classification": "new_lesson",
                }
            ],
            "grammar": [
                {
                    "candidate_id": self.grammar.id,
                    "evidence": "我喜欢喝茶",
                    "confidence": 0.90,
                    "classification": "new_lesson",
                }
            ],
        }

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_occurrence_count_aggregates_across_notes(self):
        _save_evidence(
            self.db, self.student.id, self.note1.id, self.result
        )
        _save_evidence(
            self.db, self.student.id, self.note2.id, self.result
        )
        self.db.commit()

        vocab_progress = self.db.query(
            StudentVocabularyProgress
        ).filter_by(
            student_id=self.student.id,
            vocabulary_number=self.vocab.number,
        ).one()

        grammar_progress = self.db.query(
            StudentGrammarProgress
        ).filter_by(
            student_id=self.student.id,
            grammar_point_id=self.grammar.id,
            syllabus_version="2025",
        ).one()

        self.assertEqual(vocab_progress.occurrence_count, 2)
        self.assertEqual(grammar_progress.occurrence_count, 2)
        self.assertIsNotNone(vocab_progress.first_seen_at)
        self.assertIsNotNone(vocab_progress.last_seen_at)
        self.assertLessEqual(
            vocab_progress.first_seen_at,
            vocab_progress.last_seen_at,
        )

    def test_removing_last_evidence_clears_old_dates(self):
        _save_evidence(
            self.db, self.student.id, self.note1.id, self.result
        )
        self.db.commit()

        empty_result = {
            "vocabulary": [],
            "grammar": [],
        }

        _save_evidence(
            self.db, self.student.id, self.note1.id, empty_result
        )
        self.db.commit()

        vocab_progress = self.db.query(
            StudentVocabularyProgress
        ).filter_by(
            student_id=self.student.id,
            vocabulary_number=self.vocab.number,
        ).one()

        grammar_progress = self.db.query(
            StudentGrammarProgress
        ).filter_by(
            student_id=self.student.id,
            grammar_point_id=self.grammar.id,
            syllabus_version="2025",
        ).one()

        self.assertEqual(vocab_progress.occurrence_count, 0)
        self.assertEqual(grammar_progress.occurrence_count, 0)
        self.assertIsNone(vocab_progress.first_seen_at)
        self.assertIsNone(vocab_progress.last_seen_at)
        self.assertIsNone(grammar_progress.first_seen_at)
        self.assertIsNone(grammar_progress.last_seen_at)

    def test_reanalysis_preserves_mastered_and_review_statuses(self):
        _save_evidence(
            self.db, self.student.id, self.note1.id, self.result
        )
        self.db.commit()

        vocab_progress = self.db.query(
            StudentVocabularyProgress
        ).filter_by(
            student_id=self.student.id,
            vocabulary_number=self.vocab.number,
        ).one()

        grammar_progress = self.db.query(
            StudentGrammarProgress
        ).filter_by(
            student_id=self.student.id,
            grammar_point_id=self.grammar.id,
            syllabus_version="2025",
        ).one()

        vocab_progress.learning_status = "mastered"
        grammar_progress.learning_status = "review"
        self.db.commit()

        _save_evidence(
            self.db, self.student.id, self.note1.id, self.result
        )
        self.db.commit()

        self.db.refresh(vocab_progress)
        self.db.refresh(grammar_progress)

        self.assertEqual(vocab_progress.learning_status, "mastered")
        self.assertEqual(grammar_progress.learning_status, "review")
        self.assertEqual(vocab_progress.occurrence_count, 1)
        self.assertEqual(grammar_progress.occurrence_count, 1)


if __name__ == "__main__":
    unittest.main()
