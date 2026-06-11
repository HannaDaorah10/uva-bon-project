import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from frozen_evidence import (
    EvidenceGateResult,
    FrozenEvidenceIndex,
    gate_query_evidence,
    preflight_question_gate,
)


READY = {
    "retrieve_allowed": True,
    "quote_allowed": False,
    "export_allowed": False,
    "share_external_llm_allowed": False,
    "train_allowed": False,
    "citation_ready": False,
    "user_facing_ready": False,
}


def row(**overrides):
    value = {
        "id": "test-score-row",
        "family": "kroonvolume_internal_proxy",
        "type": "score_table",
        "path": "/tmp/test-score.csv",
        "approved": True,
        "approved_for": ["internal_student_challenge"],
        "not_approved_for": [
            "public",
            "client",
            "official",
            "municipal_endorsement",
            "training",
            "external_release",
        ],
        "citation": "Test fixture only.",
        "readiness": dict(READY),
        "requires_human_review": True,
    }
    for key, item in overrides.items():
        if key == "readiness":
            value["readiness"] = item
        else:
            value[key] = item
    return value


class FrozenEvidenceTests(unittest.TestCase):
    def test_export_request_refuses_before_evidence(self):
        result = preflight_question_gate("Export the source index as a zip")

        self.assertIsInstance(result, EvidenceGateResult)
        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "export_gate_required")
        self.assertIn("export_allowed", result.blocked_gates)

    def test_action_request_refuses_before_evidence(self):
        result = preflight_question_gate("Restart the backend service and rebuild the vector index")

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "action_gate_required")

    def test_official_claim_refuses_before_evidence(self):
        result = preflight_question_gate("Is this an official municipal validated result?")

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "unsupported_claim")

    def test_route_with_missing_readiness_fails_closed(self):
        manifest = FrozenEvidenceIndex([row(readiness={"retrieve_allowed": True})])

        result = manifest.gate_route("score_table")

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "readiness_gate_blocked")
        self.assertTrue(result.missing_metadata)

    def test_route_with_denylisted_path_is_not_approved_evidence(self):
        manifest = FrozenEvidenceIndex([row(path="/home/hans/.openclaw/workspace/uva-ai-challenge/Team Platypus/uva-bon-id")])

        result = manifest.gate_route("score_table")

        self.assertTrue(result.refused)
        self.assertIn("test-score-row.denylist", result.blocked_gates)

    def test_route_requires_source_family_separation(self):
        manifest = FrozenEvidenceIndex([
            row(family="south_holland_student_retrieval", type="text_chunk_export")
        ])

        result = manifest.gate_route("score_table")

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "no_approved_evidence")

    def test_valid_route_returns_manifest_id(self):
        manifest = FrozenEvidenceIndex([row(path="/allowed/root/table.csv")])

        with mock.patch("frozen_evidence.ALLOWED_ROOTS", ("/allowed/root",)):
            with mock.patch("frozen_evidence.is_readable_file", return_value=True):
                result = manifest.gate_route("score_table")

        self.assertFalse(result.refused)
        self.assertEqual(result.manifest_ids, ["test-score-row"])
        self.assertEqual(result.evidence_family, "kroonvolume_internal_proxy")

    def test_checksum_mismatch_blocks_route(self):
        manifest = FrozenEvidenceIndex([
            row(path="/allowed/root/table.csv", checksum_sha256="not-the-real-checksum")
        ])

        with mock.patch("frozen_evidence.ALLOWED_ROOTS", ("/allowed/root",)):
            with mock.patch("frozen_evidence.is_readable_file", return_value=True):
                with mock.patch("frozen_evidence.sha256_file", return_value="abc"):
                    result = manifest.gate_route("score_table")

        self.assertTrue(result.refused)
        self.assertIn("test-score-row.checksum_sha256", result.blocked_gates)

    def test_manifest_loader_rejects_missing_manifest(self):
        result = gate_query_evidence("score_table", Path("/tmp/does-not-exist-frozen-manifest.json"))

        self.assertTrue(result.refused)
        self.assertEqual(result.refusal_reason, "no_approved_evidence")

    def test_manifest_loader_accepts_row_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.json"
            path.write_text(json.dumps([row(path="/allowed/root/table.csv")]), encoding="utf-8")

            with mock.patch("frozen_evidence.ALLOWED_ROOTS", ("/allowed/root",)):
                with mock.patch("frozen_evidence.is_readable_file", return_value=True):
                    result = gate_query_evidence("score_table", path)

        self.assertFalse(result.refused)


if __name__ == "__main__":
    unittest.main()
