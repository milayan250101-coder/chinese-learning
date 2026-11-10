import unittest
from unittest.mock import patch

from backend.student_knowledge.analysis_service import (
    KnowledgeAnalysisError,
    _BatchOutputTooLong,
    _analyze_batch_with_split,
)


class BatchSplitTests(unittest.TestCase):
    def setUp(self):
        self.vocabulary = [{"id": i} for i in range(1, 7)]
        self.grammar = [{"id": i} for i in range(101, 107)]

    def fake_result(self, vocabulary, grammar):
        return {
            "vocabulary": [
                {"candidate_id": item["id"]} for item in vocabulary
            ],
            "grammar": [
                {"candidate_id": item["id"]} for item in grammar
            ],
            "observations": [],
        }

    def test_splits_oversized_batch_and_preserves_all_candidates(self):
        calls = []

        def fake_call(note, vocabulary, grammar, history, api_key):
            vocab_ids = [item["id"] for item in vocabulary]
            grammar_ids = [item["id"] for item in grammar]
            calls.append((vocab_ids, grammar_ids))

            if len(vocabulary) + len(grammar) > 3:
                raise _BatchOutputTooLong()

            return self.fake_result(vocabulary, grammar)

        with patch(
            "backend.student_knowledge.analysis_service._call_analysis_batch",
            side_effect=fake_call,
        ):
            result = _analyze_batch_with_split(
                "课堂笔记",
                self.vocabulary,
                self.grammar,
                {},
                "test-key",
            )

        self.assertCountEqual(
            [item["id"] for item in self.vocabulary],
            [item["candidate_id"] for item in result["vocabulary"]],
        )
        self.assertCountEqual(
            [item["id"] for item in self.grammar],
            [item["candidate_id"] for item in result["grammar"]],
        )

    def test_single_candidate_still_too_long_raises_error(self):
        with patch(
            "backend.student_knowledge.analysis_service._call_analysis_batch",
            side_effect=_BatchOutputTooLong(),
        ):
            with self.assertRaisesRegex(
                KnowledgeAnalysisError,
                "单个知识点分析仍达到 AI 输出上限",
            ):
                _analyze_batch_with_split(
                    "课堂笔记",
                    [{"id": 1}],
                    [],
                    {},
                    "test-key",
                )

    def test_two_candidates_are_split_into_separate_calls(self):
        calls = []

        def fake_call(note, vocabulary, grammar, history, api_key):
            calls.append((
                [item["id"] for item in vocabulary],
                [item["id"] for item in grammar],
            ))
            if len(vocabulary) + len(grammar) > 1:
                raise _BatchOutputTooLong()
            return self.fake_result(vocabulary, grammar)

        with patch(
            "backend.student_knowledge.analysis_service._call_analysis_batch",
            side_effect=fake_call,
        ):
            result = _analyze_batch_with_split(
                "课堂笔记",
                [{"id": 1}],
                [{"id": 101}],
                {},
                "test-key",
            )

        self.assertEqual(2, len(result["vocabulary"]) + len(result["grammar"]))
        self.assertEqual(3, len(calls))
        self.assertEqual([1], [x["candidate_id"] for x in result["vocabulary"]])
        self.assertEqual([101], [x["candidate_id"] for x in result["grammar"]])


if __name__ == "__main__":
    unittest.main()
