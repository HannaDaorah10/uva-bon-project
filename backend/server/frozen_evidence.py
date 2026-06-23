"""Frozen local evidence manifest gates for the NatureDesk query API.

This module is deliberately conservative. It only validates whether a routed
question may proceed to a future retrieval handler. It does not retrieve,
summarize, quote, export, or generate answer text from evidence artifacts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST_PATH = Path(__file__).with_name("frozen_evidence_manifest.json")

APPROVED_FOR = {"internal_student_challenge", "internal_research_prototype"}
PUBLIC_DENIALS = {
    "public",
    "client",
    "official",
    "municipal_endorsement",
    "training",
    "external_release",
}
READINESS_FIELDS = {
    "retrieve_allowed",
    "quote_allowed",
    "export_allowed",
    "share_external_llm_allowed",
    "train_allowed",
    "citation_ready",
    "user_facing_ready",
}
REQUIRED_ROW_FIELDS = {
    "id",
    "family",
    "type",
    "path",
    "approved",
    "approved_for",
    "not_approved_for",
    "citation",
    "readiness",
    "requires_human_review",
}

ALLOWED_ROOTS = tuple(
    os.path.normpath(path)
    for path in (
        "/home/hans/.openclaw/workspace/kroonvolume-den-haag-openclaw/data/release/internal_research_prototype_gm0518_v1_temporal_labels_patch",
        "/home/hans/.openclaw/workspace/kroonvolume-den-haag-openclaw/data/release/internal_research_prototype_gm0518_v2_ahn5_separate_layer",
        "/home/hans/.openclaw/workspace/knowledge_base/meta_index/south_holland_lighthouse_external_ready_2026-05-26",
        "/home/hans/.openclaw/workspace/knowledge_base/methods",
        "/home/hans/.openclaw/workspace/knowledge_base/science",
        "/home/hans/.openclaw/workspace/team_comms",
        "/home/hans/.openclaw/workspace/evaluation_audit",
        "/home/hans/Documents/uva-challenge",
    )
)

ROUTE_REQUIREMENTS = {
    "text_rag": {
        "families": {"south_holland_student_retrieval"},
        "types": {"text_chunk_export"},
    },
    # This route is gated by the external Diver/Curator retrieval contract
    # rather than by a single frozen manifest row.
    "workflow_rag": {
        "families": set(),
        "types": set(),
    },
    "score_table": {
        "families": {"kroonvolume_internal_proxy"},
        "types": {"score_table"},
    },
    "map_raster": {
        "families": {"kroonvolume_internal_proxy"},
        "types": {"map_raster_pointer"},
    },
}

DENYLIST_FRAGMENTS = (
    "explicit_exclusion_list.csv",
    "/uva-bon-id",
    "private key",
    "private_key",
    "recovery code",
    "recovery_code",
    "password",
    "secret",
    "token",
    ".env",
    "connection string",
    "connection_string",
)

EXPORT_RE = re.compile(
    r"\b(export|archive|attach|download|zip|tar|bundle|source[- ]?index|release[- ]?package|csv[- ]?dump)\b",
    re.IGNORECASE,
)
ACTION_RE = re.compile(
    r"\b(update|install|restart|rerun|re-run|sudo|mutate|delete|drop|alter|rebuild|start|stop|write)\b"
    r".*\b(service|server|backend|database|db|vector|evidence|gate|pipeline|package|api)\b",
    re.IGNORECASE,
)
OFFICIAL_CLAIM_RE = re.compile(
    r"\b(official|municipal|city-endorsed|validated|validation-ready|client-ready|public-ready|ecological decision|management action)\b",
    re.IGNORECASE,
)
NEO_RE = re.compile(r"\b(neo|signaleyes|signal\s+eyes|boombasis)\b", re.IGNORECASE)
NEO_FORBIDDEN_FRAMING_RE = re.compile(
    r"\b(ground\s+truth|proof|official\s+alignment|municipal\s+equivalence|groenmonitor\s+equivalence)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceGateResult:
    refused: bool
    refusal_reason: str | None = None
    answer: str = ""
    manifest_ids: list[str] = field(default_factory=list)
    missing_metadata: list[str] = field(default_factory=list)
    blocked_gates: list[str] = field(default_factory=list)
    evidence_family: str | None = None

    def as_api_dict(self) -> dict[str, Any]:
        return {
            "manifest_ids": self.manifest_ids,
            "missing_metadata": self.missing_metadata,
            "blocked_gates": self.blocked_gates,
        }


class FrozenEvidenceError(RuntimeError):
    """Raised when the frozen evidence manifest cannot be parsed."""


@dataclass(frozen=True)
class FrozenEvidenceRow:
    raw: dict[str, Any]
    path: str

    @property
    def row_id(self) -> str:
        return str(self.raw.get("id", "<missing-id>"))

    @property
    def family(self) -> str:
        return str(self.raw.get("family", ""))

    @property
    def row_type(self) -> str:
        return str(self.raw.get("type", ""))

    @property
    def readiness(self) -> dict[str, Any]:
        value = self.raw.get("readiness")
        return value if isinstance(value, dict) else {}


class FrozenEvidenceIndex:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = [FrozenEvidenceRow(row, normalize_path(row.get("path"))) for row in rows]

    @classmethod
    def load(cls, manifest_path: Path = DEFAULT_MANIFEST_PATH) -> "FrozenEvidenceIndex":
        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError as exc:
            raise FrozenEvidenceError(f"Frozen evidence manifest missing: {manifest_path}") from exc
        except json.JSONDecodeError as exc:
            raise FrozenEvidenceError(f"Frozen evidence manifest is invalid JSON: {exc}") from exc

        rows = payload.get("rows") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise FrozenEvidenceError("Frozen evidence manifest must contain a row list")
        if not all(isinstance(row, dict) for row in rows):
            raise FrozenEvidenceError("Frozen evidence manifest rows must be objects")
        return cls(rows)

    def gate_route(self, route: str) -> EvidenceGateResult:
        requirements = ROUTE_REQUIREMENTS.get(route)
        if requirements is None:
            return EvidenceGateResult(
                refused=True,
                refusal_reason="unsupported_claim",
                answer="This query type is not supported by the frozen evidence router.",
            )

        if route == "workflow_rag":
            return EvidenceGateResult(
                refused=False,
                evidence_family="student_combined_baseline",
            )

        candidates = [
            row
            for row in self.rows
            if row.family in requirements["families"] and row.row_type in requirements["types"]
        ]
        if not candidates:
            return EvidenceGateResult(
                refused=True,
                refusal_reason="no_approved_evidence",
                answer="No approved local frozen evidence is listed for this route.",
            )

        valid_ids: list[str] = []
        families: set[str] = set()
        missing_metadata: list[str] = []
        blocked_gates: list[str] = []

        for row in candidates:
            row_missing, row_blocked = validate_row(row)
            missing_metadata.extend(row_missing)
            blocked_gates.extend(row_blocked)
            if not row_missing and not row_blocked:
                valid_ids.append(row.row_id)
                families.add(row.family)

        if valid_ids:
            evidence_family = next(iter(families)) if len(families) == 1 else None
            return EvidenceGateResult(
                refused=False,
                manifest_ids=valid_ids,
                missing_metadata=missing_metadata,
                blocked_gates=blocked_gates,
                evidence_family=evidence_family,
            )

        readiness_blocked = any(".readiness." in gate for gate in blocked_gates)
        reason = (
            "readiness_gate_blocked" if missing_metadata or readiness_blocked else "no_approved_evidence"
        )
        answer = (
            "The frozen evidence manifest has route candidates, but their readiness "
            "metadata is missing or closed."
            if reason == "readiness_gate_blocked"
            else "No approved local frozen evidence is available to the backend for this route."
        )
        return EvidenceGateResult(
            refused=True,
            refusal_reason=reason,
            answer=answer,
            missing_metadata=missing_metadata,
            blocked_gates=blocked_gates,
        )


def preflight_question_gate(question: str) -> EvidenceGateResult | None:
    if NEO_RE.search(question) and NEO_FORBIDDEN_FRAMING_RE.search(question):
        return EvidenceGateResult(
            refused=True,
            refusal_reason="unsupported_claim",
            answer=(
                "I cannot frame NEO as ground truth, proof, official alignment, "
                "municipal equivalence, or Groenmonitor equivalence. The approved "
                "framing is a local NEO dataset source-of-truth baseline under "
                "licence for non-commercial/no-fee student use, with descriptive "
                "comparison caveats."
            ),
            blocked_gates=["neo_validation_or_equivalence_claim"],
        )
    if EXPORT_RE.search(question):
        return EvidenceGateResult(
            refused=True,
            refusal_reason="export_gate_required",
            answer=(
                "I cannot export, archive, attach, or bundle source/evidence packages "
                "from /api/query without a separate approved export gate."
            ),
            blocked_gates=["export_allowed"],
        )
    if ACTION_RE.search(question):
        return EvidenceGateResult(
            refused=True,
            refusal_reason="action_gate_required",
            answer=(
                "I cannot update, install, restart, mutate, or rerun services, "
                "databases, vectors, gates, or pipelines from /api/query."
            ),
            blocked_gates=["action_allowed"],
        )
    if OFFICIAL_CLAIM_RE.search(question):
        return EvidenceGateResult(
            refused=True,
            refusal_reason="unsupported_claim",
            answer=(
                "I cannot make official, municipal, validated, public-ready, "
                "client-ready, ecological-decision, or management-action claims from "
                "this route. Human review and explicit gates are required."
            ),
            blocked_gates=["official_or_decision_claim"],
        )
    return None


def gate_query_evidence(route: str, manifest_path: Path = DEFAULT_MANIFEST_PATH) -> EvidenceGateResult:
    try:
        return FrozenEvidenceIndex.load(manifest_path).gate_route(route)
    except FrozenEvidenceError as exc:
        return EvidenceGateResult(
            refused=True,
            refusal_reason="no_approved_evidence",
            answer="The frozen evidence manifest is unavailable or invalid.",
            blocked_gates=[str(exc)],
        )


def validate_row(row: FrozenEvidenceRow) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    blocked: list[str] = []
    raw = row.raw

    for field_name in sorted(REQUIRED_ROW_FIELDS):
        if field_name not in raw:
            missing.append(f"{row.row_id}.{field_name}")

    readiness = raw.get("readiness")
    if not isinstance(readiness, dict):
        missing.append(f"{row.row_id}.readiness")
        readiness = {}

    for field_name in sorted(READINESS_FIELDS):
        if field_name not in readiness or not isinstance(readiness.get(field_name), bool):
            missing.append(f"{row.row_id}.readiness.{field_name}")

    if raw.get("approved") is not True:
        blocked.append(f"{row.row_id}.approved")

    approved_for = set(raw.get("approved_for") or [])
    not_approved_for = set(raw.get("not_approved_for") or [])
    if not approved_for.intersection(APPROVED_FOR):
        blocked.append(f"{row.row_id}.approved_for")
    if not PUBLIC_DENIALS.issubset(not_approved_for):
        blocked.append(f"{row.row_id}.not_approved_for")

    if readiness.get("retrieve_allowed") is not True:
        blocked.append(f"{row.row_id}.readiness.retrieve_allowed")
    for gate_name in ("quote_allowed", "citation_ready", "user_facing_ready"):
        if readiness.get(gate_name) is not True:
            blocked.append(f"{row.row_id}.readiness.{gate_name}")

    for gate_name in ("export_allowed", "share_external_llm_allowed", "train_allowed"):
        if readiness.get(gate_name) is not False:
            blocked.append(f"{row.row_id}.readiness.{gate_name}")

    if is_denylisted_path(row.path):
        blocked.append(f"{row.row_id}.denylist")
    if not is_under_allowed_root(row.path):
        blocked.append(f"{row.row_id}.allowed_root")
    if not is_readable_file(row.path):
        blocked.append(f"{row.row_id}.path_unavailable")

    expected_checksum = raw.get("checksum_sha256")
    if isinstance(expected_checksum, str) and expected_checksum.strip() and is_readable_file(row.path):
        actual_checksum = sha256_file(row.path)
        if actual_checksum != expected_checksum.strip().lower():
            blocked.append(f"{row.row_id}.checksum_sha256")

    return missing, blocked


def normalize_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    expanded = os.path.expanduser(value.strip())
    if not os.path.isabs(expanded):
        return ""
    return os.path.normpath(expanded)


def is_under_allowed_root(path: str) -> bool:
    if not path:
        return False
    for root in ALLOWED_ROOTS:
        try:
            if os.path.commonpath([path, root]) == root:
                return True
        except ValueError:
            continue
    return False


def is_denylisted_path(path: str) -> bool:
    lowered = path.lower()
    return any(fragment in lowered for fragment in DENYLIST_FRAGMENTS)


def is_readable_file(path: str) -> bool:
    if not path:
        return False
    try:
        file_path = Path(path)
        return file_path.is_file() and os.access(file_path, os.R_OK)
    except OSError:
        return False


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
