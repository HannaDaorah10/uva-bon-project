import unittest
from unittest import mock

try:
    from main import QueryRequest, query
except ModuleNotFoundError:  # Allows helper tests to run before requirements are installed.
    QueryRequest = None
    query = None

from frozen_evidence import EvidenceGateResult
from handlers import HandlerResponse
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

    def test_parse_workflow_rag_route(self):
        decision = parse_router_decision(
            {
                "route": "workflow_rag",
                "refusalReason": None,
                "confidence": 0.72,
                "explanation": "The question asks for controlled baseline evidence.",
            }
        )

        self.assertEqual(decision.route, "workflow_rag")
        self.assertFalse(decision.refused)
        self.assertIsNone(decision.refusal_reason)

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

    def test_crown_surface_question_routes_to_score_table_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question(
                "What is the crown surface area in the municipality of The Hague at the end of 2021?"
            )

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "score_table")

    def test_crown_surface_2020_question_routes_to_score_table_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question(
                "What is the crown surface area in the municipliaty of The Hague at the end of 2020?"
            )

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "score_table")

    def test_dutch_kroonoppervlakte_question_routes_to_score_table_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question(
                "Wat is de kroonoppervlakte in gemeente Den Haag aan het eind van 2021?"
            )

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "score_table")

    def test_iucn_baseline_question_routes_to_workflow_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question(
                "Which IUCN resolutions address indigenous peoples and protected areas?"
            )

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "workflow_rag")

    def test_neo_question_routes_to_workflow_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question(
                "What does the NEO SignalEyes Boombasis Den Haag baseline contain?"
            )

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "workflow_rag")

    def test_broad_the_hague_inventory_question_routes_to_workflow_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question("What information of The Hague do you have?")

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "workflow_rag")

    def test_messy_the_hague_inventory_question_routes_to_workflow_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question("What info do you have of The Hague?")

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "workflow_rag")

    def test_kroonvolume_map_question_routes_to_map_raster_without_model(self):
        with mock.patch("router_classifier._call_ollama") as model:
            decision = classify_question("Show the Kroonvolume Den Haag map raster pointer.")

        self.assertFalse(model.called)
        self.assertEqual(decision.route, "map_raster")

    def test_classifier_uses_mocked_model_payload(self):
        with mock.patch(
            "router_classifier._call_ollama",
            return_value={
                "route": "map_raster",
                "refusalReason": None,
                "confidence": 0.93,
                "explanation": "The question asks for a map.",
            },
        ) as ollama:
            decision = classify_question(
                "How should we inspect wetland habitat condition?",
                model="mistral:7b",
            )

        self.assertFalse(decision.refused)
        self.assertEqual(decision.route, "map_raster")
        ollama.assert_called_once_with(
            "How should we inspect wetland habitat condition?",
            model="mistral:7b",
        )

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

        with mock.patch("main.classify_question", return_value=decision) as classifier:
            response = query(QueryRequest(question="Is this legal?"))

        payload = response.model_dump(exclude_none=True)
        self.assertTrue(payload["refused"])
        self.assertEqual(payload["citations"], [])
        self.assertEqual(payload["refusalReason"], "policy_restricted")
        self.assertEqual(payload["router"]["route"], "refusal")
        self.assertNotIn("explanation", payload["router"])
        self.assertNotIn("evidence", payload)
        classifier.assert_called_once_with("Is this legal?", model="qwen2.5:7b")

    def test_query_passes_requested_model_to_classifier(self):
        decision = RouterDecision(
            route="refusal",
            refusal_reason="no_evidence",
            confidence=0.6,
            explanation="No matching evidence.",
        )

        with mock.patch("main.classify_question", return_value=decision) as classifier:
            response = query(QueryRequest(question="What does this table show?", model="mistral:7b"))

        self.assertTrue(response.refused)
        classifier.assert_called_once_with("What does this table show?", model="mistral:7b")

    def test_query_refuses_invalid_model_before_classifier(self):
        with mock.patch("main.classify_question") as classifier:
            response = query(QueryRequest(question="What does this table show?", model="../../not-a-model"))

        self.assertFalse(classifier.called)
        self.assertTrue(response.refused)
        self.assertEqual(response.refusalReason, "invalid_model")
        self.assertEqual(response.router["route"], "refusal")

    def test_query_non_refusal_route_fails_closed_after_manifest_gate(self):
        decision = RouterDecision(
            route="score_table",
            refusal_reason=None,
            confidence=0.88,
            explanation="The question asks for a table value.",
        )
        gate = EvidenceGateResult(
            refused=False,
            manifest_ids=["kroonvolume_v1_gm0518_kroonvolume_proxy_v1_csv"],
            evidence_family="kroonvolume_internal_proxy",
        )

        handler_result = HandlerResponse(
            refused=True,
            answer="Handler refuses until retrieval is ready.",
            citations=[],
            refusal_reason=BACKEND_PIPELINE_NOT_CONNECTED,
        )

        with mock.patch("main.classify_question", return_value=decision):
            with mock.patch("main.gate_query_evidence", return_value=gate):
                with mock.patch.dict("main.HANDLERS", {"score_table": lambda question, gate: handler_result}):
                    response = query(QueryRequest(question="What does the NDVI table show?"))

        payload = response.model_dump(exclude_none=True)
        self.assertTrue(payload["refused"])
        self.assertEqual(payload["citations"], [])
        self.assertEqual(payload["refusalReason"], BACKEND_PIPELINE_NOT_CONNECTED)
        self.assertEqual(payload["router"]["route"], "score_table")
        self.assertEqual(payload["router"]["confidence"], 0.88)
        self.assertEqual(payload["router"]["evidence_family"], "kroonvolume_internal_proxy")
        self.assertEqual(
            payload["evidence"]["manifest_ids"],
            ["kroonvolume_v1_gm0518_kroonvolume_proxy_v1_csv"],
        )
        self.assertNotIn("explanation", payload["router"])

    def test_query_non_refusal_route_refuses_when_manifest_gate_blocks(self):
        decision = RouterDecision(
            route="text_rag",
            refusal_reason=None,
            confidence=0.77,
            explanation="The question asks for text evidence.",
        )
        gate = EvidenceGateResult(
            refused=True,
            refusal_reason="no_approved_evidence",
            answer="No approved local frozen evidence is available to the backend.",
            blocked_gates=["south_holland_chunks_vector_ready_jsonl.path_unavailable"],
        )

        with mock.patch("main.classify_question", return_value=decision):
            with mock.patch("main.gate_query_evidence", return_value=gate):
                response = query(QueryRequest(question="What does the South Holland source say?"))

        payload = response.model_dump(exclude_none=True)
        self.assertTrue(payload["refused"])
        self.assertEqual(payload["refusalReason"], "no_approved_evidence")
        self.assertIn("path_unavailable", payload["evidence"]["blocked_gates"][0])

    def test_query_export_request_refuses_before_classifier(self):
        with mock.patch("main.classify_question") as classifier:
            response = query(QueryRequest(question="Export the source index as a zip"))

        payload = response.model_dump(exclude_none=True)
        self.assertFalse(classifier.called)
        self.assertTrue(payload["refused"])
        self.assertEqual(payload["refusalReason"], "export_gate_required")
        self.assertEqual(payload["router"]["route"], "refusal")
        self.assertIn("export_allowed", payload["evidence"]["blocked_gates"])


if __name__ == "__main__":
    unittest.main()
