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
from handlers.score_table import handle_score_table
from handlers.text_rag import handle_text_rag
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


if __name__ == "__main__":
    unittest.main()
