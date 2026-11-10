import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.hsk_models import HSKGrammarPoint, HSKVocabulary
from backend.student_knowledge.candidate_service import (
    build_knowledge_candidates,
    find_grammar_candidates,
    find_vocabulary_candidates,
)


class CandidateServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                HSKVocabulary.__table__,
                HSKGrammarPoint.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.db.add_all([
            HSKVocabulary(
                number=1, level="HSK 1",
                simplified="中国", traditional="中國",
                pinyin="Zhōngguó", english="China",
                part_of_speech="noun",
                syllabus_version="2025",
                source_repo="test", source_file="test.json",
            ),
            HSKVocabulary(
                number=2, level="HSK 1",
                simplified="中", traditional="中",
                pinyin="zhōng", english="middle",
                part_of_speech="noun",
                syllabus_version="2025",
                source_repo="test", source_file="test.json",
            ),
            HSKVocabulary(
                number=3, level="HSK 9",
                simplified="人工智能", traditional="人工智能",
                pinyin="réngōng zhìnéng", english="artificial intelligence",
                part_of_speech="noun",
                syllabus_version="2025",
                source_repo="test", source_file="test.json",
            ),
            HSKVocabulary(
                number=4, level="HSK 1",
                simplified="中国", traditional="中國",
                pinyin="Zhōngguó", english="China",
                part_of_speech="other",
                syllabus_version="2025",
                source_repo="test", source_file="test.json",
            ),
            HSKVocabulary(
                number=5, level="HSK 1",
                simplified="中国", traditional="中國",
                pinyin="Zhōngguó", english="China",
                part_of_speech="noun",
                syllabus_version="旧版本",
                source_repo="test", source_file="test.json",
            ),
        ])

        self.db.add_all([
            HSKGrammarPoint(
                id=1, level="HSK 1",
                category="sentence", category_name="句子",
                subcategory="basic", content="基础句型",
                syllabus_version="2025",
                source_repo="test", source_file="grammar.json",
                source_url="", source_index=1,
            ),
            HSKGrammarPoint(
                id=2, level="HSK 6",
                category="sentence", category_name="句子",
                subcategory="advanced", content="高级句型",
                syllabus_version="2025",
                source_repo="test", source_file="grammar.json",
                source_url="", source_index=2,
            ),
            HSKGrammarPoint(
                id=3, level="HSK 1",
                category="sentence", category_name="句子",
                subcategory="old", content="旧版本语法",
                syllabus_version="旧版本",
                source_repo="test", source_file="grammar.json",
                source_url="", source_index=3,
            ),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_matches_simplified_and_traditional(self):
        simplified = find_vocabulary_candidates(
            self.db, "我住在中国。"
        )
        traditional = find_vocabulary_candidates(
            self.db, "我住在中國。"
        )

        self.assertEqual(
            {1, 4},
            {item["id"] for item in simplified},
        )
        self.assertEqual(
            {1, 4},
            {item["id"] for item in traditional},
        )

    def test_single_character_inside_word_is_not_independent(self):
        candidates = find_vocabulary_candidates(
            self.db, "我住在中国。"
        )
        candidate_ids = {item["id"] for item in candidates}

        self.assertIn(1, candidate_ids)
        self.assertNotIn(2, candidate_ids)

    def test_single_character_is_kept_when_independent(self):
        candidates = find_vocabulary_candidates(
            self.db, "我住在中国，我在中间。"
        )
        candidate_ids = {item["id"] for item in candidates}

        self.assertIn(2, candidate_ids)

    def test_hsk_9_vocabulary_is_supported(self):
        candidates = find_vocabulary_candidates(
            self.db, "人工智能正在发展。"
        )

        self.assertIn(
            3,
            {item["id"] for item in candidates},
        )

    def test_same_word_records_are_not_merged(self):
        candidates = find_vocabulary_candidates(
            self.db, "中国"
        )
        matching = [
            item for item in candidates
            if item["simplified"] == "中国"
        ]

        self.assertEqual(2, len(matching))
        self.assertEqual({1, 4}, {item["id"] for item in matching})

    def test_only_requested_syllabus_version_is_used(self):
        candidates = find_vocabulary_candidates(
            self.db, "中国", syllabus_version="2025"
        )

        self.assertNotIn(
            5,
            {item["id"] for item in candidates},
        )

    def test_grammar_candidates_include_all_available_levels(self):
        candidates = find_grammar_candidates(self.db)

        self.assertEqual(
            {1, 2},
            {item["id"] for item in candidates},
        )
        self.assertEqual(
            ["HSK 1", "HSK 6"],
            [item["level"] for item in candidates],
        )

    def test_build_candidates_rejects_empty_notes(self):
        with self.assertRaises(ValueError):
            build_knowledge_candidates(self.db, "   ")


if __name__ == "__main__":
    unittest.main()
