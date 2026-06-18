import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from frozen_evidence import EvidenceGateResult, FrozenEvidenceIndex
from handlers import HandlerResponse
from handlers.map_raster import handle_map_raster
from handlers.score_table_dynamic import handle_score_table
from handlers.text_rag import handle_text_rag
from handlers.workflow_rag import (
    THE_HAGUE_OVERVIEW_QUERY,
    handle_workflow_rag,
    parse_query_understanding_payload,
    retrieval_question_for_user_question,
    retrieval_questions_for_user_question,
)
from router_classifier import RouterDecision

try:
    import fastapi  # noqa: F401
    import pydantic  # noqa: F401
except ModuleNotFoundError:
    fastapi_stub = types.ModuleType("fastapi")
    pydantic_stub = types.ModuleType("pydantic")

    class FastAPI:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return lambda func: func

        def post(self, *args, **kwargs):
            return lambda func: func

    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def model_dump(self, exclude_none=False):
            payload = dict(self.__dict__)
            if exclude_none:
                payload = {key: value for key, value in payload.items() if value is not None}
            return payload

    def Field(default, **kwargs):
        return default

    fastapi_stub.FastAPI = FastAPI
    pydantic_stub.BaseModel = BaseModel
    pydantic_stub.Field = Field
    sys.modules.setdefault("fastapi", fastapi_stub)
    sys.modules.setdefault("pydantic", pydantic_stub)

from main import QueryRequest, query


READY = {
    "retrieve_allowed": True,
    "quote_allowed": True,
    "export_allowed": False,
    "share_external_llm_allowed": False,
    "train_allowed": False,
    "citation_ready": True,
    "user_facing_ready": True,
}


CLOSED_ANSWER_READINESS = dict(READY)
CLOSED_ANSWER_READINESS["quote_allowed"] = False
CLOSED_ANSWER_READINESS["citation_ready"] = False
CLOSED_ANSWER_READINESS["user_facing_ready"] = False


DENIALS = [
    "public",
    "client",
    "official",
    "municipal_endorsement",
    "training",
    "external_release",
]


def manifest_row(row_id, family, row_type, path, readiness=None):
    return {
        "id": row_id,
        "family": family,
        "type": row_type,
        "path": str(path),
        "relative_path": Path(path).name,
        "approved": True,
        "approved_for": ["internal_student_challenge"],
        "not_approved_for": list(DENIALS),
        "citation": "Internal demo fixture; not official, not validated, not public/client ready.",
        "readiness": dict(readiness or READY),
        "requires_human_review": True,
        "caveat_flags": ["not_official_not_validated"],
    }


def gate(row_id, family="kroonvolume_internal_proxy"):
    return EvidenceGateResult(
        refused=False,
        manifest_ids=[row_id],
        evidence_family=family,
    )


def workflow_gate():
    return EvidenceGateResult(
        refused=False,
        evidence_family="student_combined_baseline",
    )


def workflow_payload(relevance_label="strong", sufficient=True):
    chunk = {
        "chunk_id": "chunk-1",
        "document_id": "doc-1",
        "title": "Kroonvolume Den Haag summary",
        "year": 2026,
        "section_heading": "validation",
        "page_start": None,
        "page_end": None,
        "cosine_distance": 0.32,
        "chunk_text": "Den Haag Kroonvolume evidence has denominator and validation caveats.",
        "source_path": "approved_release:validation_readiness_matrix_v1.csv",
        "citation_string": "Kroonvolume Den Haag internal research prototype summary.",
        "source_family": "Kroonvolume Den Haag internal research prototype",
        "allowed_uses": ["internal_student_prototype_retrieval_assessment", "analyst_review"],
        "citation_ready": False,
        "analyst_citation_ready": False,
        "user_facing_ready": False,
        "share_with_external_llm": False,
        "train_allowed": False,
        "namespace": "kroonvolume_den_haag_student_baseline",
        "retrieval_mode": "read_only_pgvector",
        "run_id": "test-run",
    }
    return {
        "retrieval_package": {
            "schema_version": "retrieval_package.v1",
            "status": "success",
            "run_id": "test-run",
            "namespace": "student_combined_baseline",
            "chunks": [chunk],
            "failure": None,
        },
        "source_assessment": {
            "schema_version": "source_assessment.v1",
            "status": "success",
            "sufficient_evidence": sufficient,
            "source_assessments": [
                {
                    "chunk_id": "chunk-1",
                    "document_id": "doc-1",
                    "citation_string": "Kroonvolume Den Haag internal research prototype summary.",
                    "relevance_label": relevance_label,
                    "relevance_score": 0.68,
                    "evidence_use": "candidate_source_only",
                    "insufficient_reason": None,
                }
            ],
        },
    }


class DemoHandlerSmokeTests(unittest.TestCase):
    def test_score_table_answer_uses_readable_approved_csv_and_citations(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "score.csv"
            table_path.write_text("area,ndvi,score\nGM0518,0.42,green\n", encoding="utf-8")
            row = manifest_row(
                "score-row",
                "kroonvolume_internal_proxy",
                "score_table",
                table_path,
            )

            with mock.patch("handlers.FrozenEvidenceIndex.load", return_value=FrozenEvidenceIndex([row])):
                with mock.patch("frozen_evidence.ALLOWED_ROOTS", (str(tmpdir),)):
                    result = handle_score_table("What is in the score table?", gate("score-row"))

        self.assertFalse(result.refused)
        self.assertIn("Rows detected: 1", result.answer)
        self.assertEqual(result.citations[0]["manifest_id"], "score-row")

    def test_crown_surface_2020_uses_municipality_proxy_row(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = Path(tmpdir) / "gm0518_kroonvolume_proxy_v1.csv"
            table_path.write_text(
                "\n".join(
                    [
                        "ahn_generation,acquisition_period,aggregation_level,aggregation_unit_id,aggregation_unit_name,municipality_code,candidate_area_m2,candidate_area_ha,uncertainty_class,caveat_flags",
                        "AHN3,2014-2019,gemeente,GM0518,'s-Gravenhage,GM0518,12191374.5,1219.13745,high,not_official",
                        "AHN4,2020-2022,gemeente,GM0518,'s-Gravenhage,GM0518,11187481.25,1118.748125,high,not_official",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            row = manifest_row(
                "score-row",
                "kroonvolume_internal_proxy",
                "score_table",
                table_path,
            )
            row["relative_path"] = "gm0518_kroonvolume_proxy_v1.csv"

            with mock.patch("handlers.FrozenEvidenceIndex.load", return_value=FrozenEvidenceIndex([row])):
                with mock.patch("frozen_evidence.ALLOWED_ROOTS", (str(tmpdir),)):
                    result = handle_score_table(
                        "What is the crown surface area in the municipliaty of The Hague at the end of 2020?",
                        gate("score-row"),
                    )

        self.assertFalse(result.refused)
        self.assertIn("11,187,481.25 m2", result.answer)
        self.assertIn("AHN4", result.answer)
        self.assertIn("2020-2022", result.answer)

    def test_score_table_refuses_when_approved_file_unreadable(self):
        row = manifest_row(
            "score-row",
            "kroonvolume_internal_proxy",
            "score_table",
            "/not/allowed/missing.csv",
        )

        with mock.patch("handlers.FrozenEvidenceIndex.load", return_value=FrozenEvidenceIndex([row])):
            result = handle_score_table("What is in the score table?", gate("score-row"))

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "no_approved_evidence")

    def test_text_rag_refuses_when_answer_readiness_is_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            chunks_path = Path(tmpdir) / "chunks.jsonl"
            chunks_path.write_text(json.dumps({"chunk_text": "approved fixture text"}) + "\n", encoding="utf-8")
            row = manifest_row(
                "text-row",
                "south_holland_student_retrieval",
                "text_chunk_export",
                chunks_path,
                readiness=CLOSED_ANSWER_READINESS,
            )

            with mock.patch("handlers.FrozenEvidenceIndex.load", return_value=FrozenEvidenceIndex([row])):
                with mock.patch("frozen_evidence.ALLOWED_ROOTS", (str(tmpdir),)):
                    result = handle_text_rag("What does the text say?", gate("text-row", "south_holland_student_retrieval"))

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "no_approved_evidence")

    def test_map_raster_returns_pointer_with_citation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stac_path = Path(tmpdir) / "stac_collection.json"
            stac_path.write_text(
                json.dumps({"id": "kroon-demo", "title": "Kroon demo rasters", "links": [{"href": "item.json"}]}),
                encoding="utf-8",
            )
            row = manifest_row(
                "map-row",
                "kroonvolume_internal_proxy",
                "map_raster_pointer",
                stac_path,
            )

            with mock.patch("handlers.FrozenEvidenceIndex.load", return_value=FrozenEvidenceIndex([row])):
                with mock.patch("frozen_evidence.ALLOWED_ROOTS", (str(tmpdir),)):
                    result = handle_map_raster("Show the raster map pointer", gate("map-row"))

        self.assertFalse(result.refused)
        self.assertIn("Approved map/raster pointer", result.answer)
        self.assertEqual(result.citations[0]["manifest_id"], "map-row")

    def test_workflow_rag_returns_trace_only_answer(self):
        with mock.patch(
            "handlers.workflow_rag.run_diver_curator_workflow",
            return_value=(workflow_payload(), None),
        ):
            result = handle_workflow_rag(
                "Find Kroonvolume Den Haag evidence about denominator caveats.",
                workflow_gate(),
            )

        self.assertFalse(result.refused)
        self.assertIn("Diver/Curator retrieval", result.answer)
        self.assertEqual(result.citations[0]["trace_type"], "retrieval_package.v1")
        self.assertEqual(result.citations[0]["readiness"]["user_facing_ready"], False)

    def test_workflow_rag_expands_broad_the_hague_inventory_question(self):
        with mock.patch(
            "handlers.workflow_rag.run_diver_curator_workflow",
            return_value=(workflow_payload(), None),
        ) as workflow:
            result = handle_workflow_rag(
                "What information of The Hague do you have?",
                workflow_gate(),
            )

        self.assertFalse(result.refused)
        workflow.assert_called_once_with(THE_HAGUE_OVERVIEW_QUERY)

    def test_workflow_rag_understands_messy_the_hague_inventory_phrasings(self):
        questions = [
            "What info do you have of The Hague?",
            "What information do you have of The Hague?",
            "Do we have anything on Den Haag?",
            "What have we got for GM0518?",
            "Tell me about available material for 's-Gravenhage",
        ]

        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(
                    retrieval_question_for_user_question(question),
                    THE_HAGUE_OVERVIEW_QUERY,
                )

    def test_workflow_rag_treats_info_and_information_the_same(self):
        info_plan = retrieval_questions_for_user_question("What info do you have of The Hague?")
        information_plan = retrieval_questions_for_user_question(
            "What information do you have of The Hague?"
        )

        self.assertEqual(info_plan[0], THE_HAGUE_OVERVIEW_QUERY)
        self.assertEqual(information_plan[0], THE_HAGUE_OVERVIEW_QUERY)
        self.assertEqual(len(info_plan), 2)
        self.assertEqual(len(information_plan), 2)

    def test_workflow_rag_retrieval_plan_keeps_literal_fallback(self):
        questions = retrieval_questions_for_user_question("What info do you have of The Hague?")

        self.assertEqual(questions[0], THE_HAGUE_OVERVIEW_QUERY)
        self.assertEqual(questions[1], "What info do you have of The Hague?")

    def test_workflow_rag_keeps_unrelated_short_the_hague_questions_literal(self):
        questions = [
            "The Hague weather?",
            "The Hague mayor?",
            "Is The Hague safe?",
        ]

        for question in questions:
            with self.subTest(question=question):
                self.assertEqual(retrieval_questions_for_user_question(question), [question])

    def test_workflow_rag_keeps_narrow_den_haag_evidence_questions_literal(self):
        question = "Find Kroonvolume Den Haag evidence about denominator caveats."

        self.assertEqual(retrieval_questions_for_user_question(question), [question])

    def test_workflow_rag_uses_local_llm_only_as_bounded_intent_fallback(self):
        with mock.patch(
            "handlers.workflow_rag.call_query_understanding_llm",
            return_value={
                "intent": "place_inventory",
                "placeKey": "the_hague",
                "confidence": 0.91,
                "answer": "Ignored model answer.",
                "canonicalQuery": "Ignored model query.",
            },
        ) as llm:
            questions = retrieval_questions_for_user_question(
                "Wat hebben we lokaal over Den Haag?",
                model="gemma2:9b",
            )

        self.assertEqual(questions[0], THE_HAGUE_OVERVIEW_QUERY)
        self.assertEqual(questions[1], "Wat hebben we lokaal over Den Haag?")
        llm.assert_called_once_with("Wat hebben we lokaal over Den Haag?", model="gemma2:9b")

    def test_workflow_rag_ignores_local_llm_for_blocked_place_questions(self):
        with mock.patch("handlers.workflow_rag.call_query_understanding_llm") as llm:
            questions = retrieval_questions_for_user_question("Who is the mayor of The Hague today?")

        self.assertFalse(llm.called)
        self.assertEqual(questions, ["Who is the mayor of The Hague today?"])

    def test_workflow_rag_falls_back_to_literal_when_local_llm_unavailable(self):
        with mock.patch(
            "handlers.workflow_rag.call_query_understanding_llm",
            side_effect=RuntimeError("offline"),
        ):
            questions = retrieval_questions_for_user_question("Wat hebben we lokaal over Den Haag?")

        self.assertEqual(questions, ["Wat hebben we lokaal over Den Haag?"])

    def test_workflow_rag_rejects_unapproved_model_place_or_low_confidence(self):
        self.assertIsNone(
            parse_query_understanding_payload(
                {
                    "intent": "place_inventory",
                    "placeKey": "rotterdam",
                    "confidence": 0.99,
                }
            )
        )
        self.assertIsNone(
            parse_query_understanding_payload(
                {
                    "intent": "place_inventory",
                    "placeKey": "the_hague",
                    "confidence": 0.2,
                }
            )
        )

    def test_workflow_rag_falls_back_to_literal_question_after_weak_canonical_query(self):
        with mock.patch(
            "handlers.workflow_rag.run_diver_curator_workflow",
            side_effect=[
                (workflow_payload(relevance_label="weak", sufficient=False), None),
                (workflow_payload(), None),
            ],
        ) as workflow:
            result = handle_workflow_rag(
                "What info do you have of The Hague?",
                workflow_gate(),
            )

        self.assertFalse(result.refused)
        self.assertEqual(workflow.call_args_list[0].args[0], THE_HAGUE_OVERVIEW_QUERY)
        self.assertEqual(workflow.call_args_list[1].args[0], "What info do you have of The Hague?")

    def test_workflow_rag_does_not_fallback_after_contract_failure(self):
        with mock.patch(
            "handlers.workflow_rag.run_diver_curator_workflow",
            return_value=(None, "workflow unavailable"),
        ) as workflow:
            result = handle_workflow_rag(
                "What info do you have of The Hague?",
                workflow_gate(),
            )

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "retrieval_contract_unavailable")
        workflow.assert_called_once_with(THE_HAGUE_OVERVIEW_QUERY)

    def test_workflow_rag_refuses_weak_evidence(self):
        with mock.patch(
            "handlers.workflow_rag.run_diver_curator_workflow",
            return_value=(workflow_payload(relevance_label="weak", sufficient=True), None),
        ):
            result = handle_workflow_rag(
                "Find Kroonvolume Den Haag evidence about denominator caveats.",
                workflow_gate(),
            )

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "insufficient_evidence")


class DemoApiRefusalSmokeTests(unittest.TestCase):
    def test_export_archive_refusal_precedes_classifier(self):
        with mock.patch("main.classify_question") as classifier:
            response = query(QueryRequest(question="Archive and export the evidence bundle"))

        self.assertFalse(classifier.called)
        self.assertTrue(response.refused)
        self.assertEqual(response.refusalReason, "export_gate_required")

    def test_restart_rerun_refusal_precedes_classifier(self):
        with mock.patch("main.classify_question") as classifier:
            response = query(QueryRequest(question="Restart the backend service and rerun the evidence pipeline"))

        self.assertFalse(classifier.called)
        self.assertTrue(response.refused)
        self.assertEqual(response.refusalReason, "action_gate_required")

    def test_official_public_validated_claim_refusal_precedes_classifier(self):
        with mock.patch("main.classify_question") as classifier:
            response = query(QueryRequest(question="Is this official validated public-ready evidence?"))

        self.assertFalse(classifier.called)
        self.assertTrue(response.refused)
        self.assertEqual(response.refusalReason, "unsupported_claim")

    def test_live_web_gbif_request_refuses(self):
        decision = RouterDecision(
            route="refusal",
            refusal_reason="live_data_not_allowed",
            confidence=1.0,
            explanation="Live web or GBIF request.",
        )
        with mock.patch("main.classify_question", return_value=decision):
            response = query(QueryRequest(question="Use live GBIF web data today"))

        self.assertTrue(response.refused)
        self.assertEqual(response.refusalReason, "live_data_not_allowed")
        self.assertEqual(response.citations, [])

    def test_no_non_refusal_answer_without_citations(self):
        decision = RouterDecision(
            route="score_table",
            refusal_reason=None,
            confidence=0.9,
            explanation="score table",
        )
        evidence_gate = EvidenceGateResult(
            refused=False,
            manifest_ids=["score-row"],
            evidence_family="kroonvolume_internal_proxy",
        )
        uncited = HandlerResponse(refused=False, answer="uncited answer", citations=[])

        with mock.patch("main.classify_question", return_value=decision):
            with mock.patch("main.gate_query_evidence", return_value=evidence_gate):
                with mock.patch.dict("main.HANDLERS", {"score_table": lambda question, gate: uncited}):
                    response = query(QueryRequest(question="What does the score table show?"))

        self.assertTrue(response.refused)
        self.assertEqual(response.refusalReason, "citation_validation_failed")
        self.assertEqual(response.citations, [])

    def test_workflow_rag_answer_passes_trace_citation_validation(self):
        decision = RouterDecision(
            route="workflow_rag",
            refusal_reason=None,
            confidence=0.9,
            explanation="combined baseline",
        )
        evidence_gate = EvidenceGateResult(
            refused=False,
            evidence_family="student_combined_baseline",
        )

        with mock.patch("main.classify_question", return_value=decision):
            with mock.patch("main.gate_query_evidence", return_value=evidence_gate):
                with mock.patch(
                    "handlers.workflow_rag.run_diver_curator_workflow",
                    return_value=(workflow_payload(), None),
                ):
                    response = query(QueryRequest(question="Find Kroonvolume Den Haag evidence about validation."))

        self.assertFalse(response.refused)
        self.assertEqual(response.router["route"], "workflow_rag")
        self.assertEqual(response.citations[0]["trace_type"], "retrieval_package.v1")

    def test_query_model_reaches_workflow_query_understanding(self):
        decision = RouterDecision(
            route="workflow_rag",
            refusal_reason=None,
            confidence=0.9,
            explanation="combined baseline",
        )
        evidence_gate = EvidenceGateResult(
            refused=False,
            evidence_family="student_combined_baseline",
        )

        with mock.patch("main.classify_question", return_value=decision):
            with mock.patch("main.gate_query_evidence", return_value=evidence_gate):
                with mock.patch(
                    "handlers.workflow_rag.call_query_understanding_llm",
                    return_value={
                        "intent": "place_inventory",
                        "placeKey": "the_hague",
                        "confidence": 0.91,
                    },
                ) as llm:
                    with mock.patch(
                        "handlers.workflow_rag.run_diver_curator_workflow",
                        return_value=(workflow_payload(), None),
                    ) as workflow:
                        response = query(
                            QueryRequest(
                                question="Wat hebben we lokaal over Den Haag?",
                                model="gemma2:9b",
                            )
                        )

        self.assertFalse(response.refused)
        llm.assert_called_once_with("Wat hebben we lokaal over Den Haag?", model="gemma2:9b")
        workflow.assert_called_once_with(THE_HAGUE_OVERVIEW_QUERY)


if __name__ == "__main__":
    unittest.main()
