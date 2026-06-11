import unittest
from unittest import mock

try:
    from main import QueryRequest, query
except ModuleNotFoundError:  # Allows helper tests to run before requirements are installed.
    QueryRequest = None
    query = None

from router_classifier import BACKEND_PIPELINE_NOT_CONNECTED, RouterDecision
from router_classifier import (
    RouterClassificationError,
    classify_question,
    extract_json_object,
    parse_router_decision,
    refusal_answer,
)


class RouterClassifierTests(unittest.TestCase):
    def test_parse_score_table_route(self):
        decision = parse_router_decision(
            {
                "route": "score_table",
                "refusalReason": None,
                "confidence": 0.84,
                "explanation": "The question asks for an exact indicator value.",
            }
        )

        self.assertEqual(decision.route, "score_table")
        self.assertFalse(decision.refused)
        self.assertIsNone(decision.refusal_reason)
        self.assertEqual(decision.confidence, 0.84)

    def test_parse_refusal_defaults_unknown_reason(self):
        decision = parse_router_decision(
            {
                "route": "refusal",
                "refusalReason": "unknown",
                "confidence": 2,
                "explanation": "",
            }
        )

        self.assertTrue(decision.refused)
        self.assertEqual(decision.refusal_reason, "no_evidence")
        self.assertEqual(decision.confidence, 1.0)
        self.assertTrue(decision.explanation)

    def test_extract_json_from_wrapped_output(self):
        payload = extract_json_object(
            'Here is the result: {"route":"text_rag","confidence":0.7}'
        )

        self.assertEqual(payload["route"], "text_rag")

    def test_extract_json_rejects_missing_json(self):
        with self.assertRaises(RouterClassificationError):
            extract_json_object("not json")

    def test_classifier_fails_closed_when_ollama_unavailable(self):
        with mock.patch(
            "router_classifier._call_ollama",
            side_effect=RuntimeError("offline"),
        ):
            decision = classify_question("What does this table show?")

        self.assertTrue(decision.refused)
        self.assertEqual(decision.refusal_reason, "classifier_unavailable")

    def test_classifier_uses_mocked_model_payload(self):
        with mock.patch(
            "router_classifier._call_ollama",
            return_value={
                "route": "map_raster",
                "refusalReason": None,
                "confidence": 0.93,
                "explanation": "The question asks for a map.",
            },
        ):
            decision = classify_question("Show a map of wetland habitat.")

        self.assertFalse(decision.refused)
        self.assertEqual(decision.route, "map_raster")

    def test_refusal_answer_is_human_readable(self):
        answer = refusal_answer("live_data_not_allowed")

        self.assertIn("live", answer.lower())


@unittest.skipIf(QueryRequest is None or query is None, "FastAPI is not installed")
class QueryApiTests(unittest.TestCase):
    def test_query_refusal_response_shape(self):
        decision = RouterDecision(
            route="refusal",
            refusal_reason="policy_restricted",
            confidence=0.9,
            explanation="Legal or policy advice is out of scope.",
        )

        with mock.patch("main.classify_question", return_value=decision):
            response = query(QueryRequest(question="Is this legal?"))

        payload = response.model_dump(exclude_none=True)
        self.assertTrue(payload["refused"])
        self.assertEqual(payload["citations"], [])
        self.assertEqual(payload["refusalReason"], "policy_restricted")
        self.assertEqual(payload["router"]["route"], "refusal")
        self.assertNotIn("explanation", payload["router"])

    def test_query_non_refusal_route_fails_closed(self):
        decision = RouterDecision(
            route="score_table",
            refusal_reason=None,
            confidence=0.88,
            explanation="The question asks for a table value.",
        )

        with mock.patch("main.classify_question", return_value=decision):
            response = query(QueryRequest(question="What does the NDVI table show?"))

        payload = response.model_dump(exclude_none=True)
        self.assertTrue(payload["refused"])
        self.assertEqual(payload["citations"], [])
        self.assertEqual(payload["refusalReason"], BACKEND_PIPELINE_NOT_CONNECTED)
        self.assertEqual(payload["router"]["route"], "score_table")
        self.assertEqual(payload["router"]["confidence"], 0.88)
        self.assertNotIn("explanation", payload["router"])


if __name__ == "__main__":
    unittest.main()
