import unittest

from backend.student_knowledge.analysis_service import (
    KnowledgeAnalysisError,
    _parse_json_response,
    _validate_results,
)


class AnalysisValidationTests(unittest.TestCase):
    def setUp(self):
        self.note = (
            "老师讲解了虽然天气很冷，但是我们还是去学校。"
            "学生练习了虽然下雨，但是继续上课。"
        )
        self.vocabulary = [{"id": 101}]
        self.grammar = [{"id": 201}]

    def result(self, vocabulary=None, grammar=None, observations=None):
        return {
            "vocabulary": vocabulary or [],
            "grammar": grammar or [],
            "observations": observations or [],
        }

    def item(self, candidate_id=201, evidence=None, **kwargs):
        data = {
            "candidate_id": candidate_id,
            "evidence": evidence or "虽然天气很冷",
            "confidence": 0.9,
            "classification": "uncertain",
            "classification_reason": "课堂原文证据",
            "teaching_signals": [],
        }
        data.update(kwargs)
        return data

    def validate(self, result, prior_knowledge=None):
        return _validate_results(
            result=result,
            note_text=self.note,
            vocabulary_candidates=self.vocabulary,
            grammar_candidates=self.grammar,
            prior_knowledge=prior_knowledge,
        )

    def test_rejects_unknown_candidate_id(self):
        result = self.result(
            grammar=[self.item(candidate_id=999)]
        )
        validated = self.validate(result)
        self.assertEqual([], validated["grammar"])

    def test_rejects_evidence_not_in_current_note(self):
        result = self.result(
            grammar=[self.item(evidence="我喜欢苹果")]
        )
        validated = self.validate(result)
        self.assertEqual([], validated["grammar"])

    def test_rejects_invalid_confidence(self):
        for confidence in ("invalid", -0.1, 1.1, None):
            with self.subTest(confidence=confidence):
                result = self.result(
                    grammar=[self.item(confidence=confidence)]
                )
                validated = self.validate(result)
                self.assertEqual([], validated["grammar"])

    def test_downgrades_previous_exposure_without_history(self):
        result = self.result(
            grammar=[self.item(classification="previously_exposed")]
        )
        validated = self.validate(result)
        self.assertEqual(
            "uncertain",
            validated["grammar"][0]["classification"],
        )

    def test_keeps_previous_exposure_with_history_evidence(self):
        result = self.result(
            grammar=[self.item(classification="previously_exposed")]
        )
        history = {
            "grammar": [{
                "candidate_id": 201,
                "evidence": "以前课堂中出现过",
            }]
        }
        validated = self.validate(result, history)
        self.assertEqual(
            "previously_exposed",
            validated["grammar"][0]["classification"],
        )

    def test_downgrades_new_lesson_without_teaching_signal(self):
        result = self.result(
            grammar=[self.item(classification="new_lesson")]
        )
        validated = self.validate(result)
        self.assertEqual(
            "uncertain",
            validated["grammar"][0]["classification"],
        )

    def test_keeps_new_lesson_with_explicit_explanation(self):
        result = self.result(
            grammar=[self.item(
                classification="new_lesson",
                teaching_signals=["explicit_explanation"],
            )]
        )
        validated = self.validate(result)
        self.assertEqual(
            "new_lesson",
            validated["grammar"][0]["classification"],
        )

    def test_two_verified_examples_can_support_new_lesson(self):
        result = self.result(
            grammar=[self.item(
                classification="new_lesson",
                teaching_signals=["example"],
                supporting_evidence=[
                    "虽然天气很冷",
                    "虽然下雨",
                ],
            )]
        )
        validated = self.validate(result)
        self.assertEqual(
            "new_lesson",
            validated["grammar"][0]["classification"],
        )

    def test_unverified_examples_cannot_support_new_lesson(self):
        result = self.result(
            grammar=[self.item(
                classification="new_lesson",
                teaching_signals=["example"],
                supporting_evidence=[
                    "虽然天气很冷",
                    "我喜欢苹果",
                ],
            )]
        )
        validated = self.validate(result)
        self.assertEqual(
            "uncertain",
            validated["grammar"][0]["classification"],
        )

    def test_duplicate_evidence_is_kept_only_once(self):
        result = self.result(
            grammar=[
                self.item(),
                self.item(),
            ]
        )
        validated = self.validate(result)
        self.assertEqual(1, len(validated["grammar"]))

    def test_invalid_teaching_signals_are_removed(self):
        result = self.result(
            grammar=[self.item(
                teaching_signals=[
                    "explicit_explanation",
                    "unknown_signal",
                    "example",
                ]
            )]
        )
        validated = self.validate(result)
        self.assertEqual(
            ["explicit_explanation", "example"],
            validated["grammar"][0]["teaching_signals"],
        )

    def test_observations_are_trimmed_and_limited(self):
        result = self.result(
            observations=["  课堂内容正常  ", "x" * 600]
        )
        validated = self.validate(result)
        self.assertEqual("课堂内容正常", validated["observations"][0])
        self.assertEqual(500, len(validated["observations"][1]))

    def test_parser_accepts_markdown_json_fence(self):
        parsed = _parse_json_response(
            '```json\n{"vocabulary": [], "grammar": []}\n```'
        )
        self.assertEqual([], parsed["vocabulary"])

    def test_parser_rejects_invalid_json(self):
        with self.assertRaises(KnowledgeAnalysisError):
            _parse_json_response("这不是有效 JSON")


if __name__ == "__main__":
    unittest.main()
