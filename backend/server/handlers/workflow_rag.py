"""Diver/Curator retrieval-contract handler.

This handler connects the assistant to the same controlled retrieval shape used
by the Platypus agent: retrieval_package.v1 followed by source_assessment.v1.
It fails closed when the workflow is unavailable, weak, or missing source trace.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from frozen_evidence import EvidenceGateResult
from handlers import HandlerResponse, safe_refusal
from synthesis import synthesize_workflow_answer


DEFAULT_WORKFLOW_PATH = "/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py"
DEFAULT_NAMESPACE = "student_combined_baseline"
DEFAULT_TOP_K = 5
DEFAULT_TIMEOUT_SECONDS = 75
NEO_NAMESPACE = "neo_den_haag_student_baseline"
NEO_TOP_K = 8
NEO_QUERY_TERMS = ("neo", "signaleyes", "signal eyes", "boombasis")
USABLE_RELEVANCE_LABELS = {"strong", "moderate", "usable", "partial"}
INTERNAL_ALLOWED_USES = {
    "internal_student_prototype_retrieval_assessment",
    "internal_student_challenge",
    "internal_research_prototype",
    "analyst_review",
}


def handle_workflow_rag(question: str, gate: EvidenceGateResult) -> HandlerResponse:
    if gate.refused:
        return safe_refusal(
            gate.refusal_reason or "readiness_gate_blocked",
            gate.answer or "The retrieval contract gate refused this request.",
        )

    payload, failure = run_diver_curator_workflow(question)
    if failure is not None:
        return safe_refusal("retrieval_contract_unavailable", failure)

    retrieval = payload.get("retrieval_package")
    assessment = payload.get("source_assessment")
    if not isinstance(retrieval, dict) or not isinstance(assessment, dict):
        return safe_refusal(
            "retrieval_contract_failed",
            "The retrieval workflow did not return the required retrieval and assessment contract.",
        )

    failure_payload = retrieval.get("failure")
    if retrieval.get("status") != "success" or failure_payload:
        failure_type = "retrieval_contract_failed"
        if isinstance(failure_payload, dict) and isinstance(failure_payload.get("type"), str):
            failure_type = failure_payload["type"]
        return safe_refusal(
            failure_type,
            "The controlled retrieval workflow failed, so I cannot answer from approved evidence.",
        )

    if assessment.get("status") != "success" or assessment.get("sufficient_evidence") is not True:
        return safe_refusal(
            "insufficient_evidence",
            "The controlled retrieval workflow did not find enough strong or moderate evidence.",
        )

    usable_items = usable_workflow_items(retrieval, assessment)
    if not usable_items:
        return safe_refusal(
            "insufficient_evidence",
            "The controlled retrieval workflow returned no usable source traces for an answer.",
        )

    citations = [citation_for_workflow_item(item) for item in usable_items]
    answer = synthesize_workflow_answer(question, usable_items)
    return HandlerResponse(refused=False, answer=answer, citations=citations)


def run_diver_curator_workflow(question: str) -> tuple[dict[str, Any] | None, str | None]:
    workflow_path = os.environ.get("NATUREDESK_DIVER_CURATOR_WORKFLOW", DEFAULT_WORKFLOW_PATH)
    namespace = os.environ.get("NATUREDESK_RETRIEVAL_NAMESPACE") or namespace_for_question(question)
    default_top_k = NEO_TOP_K if namespace == NEO_NAMESPACE else DEFAULT_TOP_K
    top_k = _int_from_env("NATUREDESK_RETRIEVAL_TOP_K", default_top_k)
    timeout_seconds = _int_from_env("NATUREDESK_RETRIEVAL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)

    script = Path(workflow_path)
    if not script.is_file():
        return None, (
            "The controlled retrieval workflow is not available to the backend runtime. "
            "Set NATUREDESK_DIVER_CURATOR_WORKFLOW to a readable workflow path."
        )

    cmd = [
        sys.executable,
        str(script),
        "--namespace",
        namespace,
        "--question",
        question,
        "--top-k",
        str(top_k),
    ]
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, "The controlled retrieval workflow could not be executed in time."

    if proc.returncode != 0:
        return None, "The controlled retrieval workflow exited with an error."

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, "The controlled retrieval workflow returned invalid JSON."

    if not isinstance(payload, dict):
        return None, "The controlled retrieval workflow returned an unexpected payload."
    return payload, None


def namespace_for_question(question: str) -> str:
    lowered = question.lower()
    if any(term in lowered for term in NEO_QUERY_TERMS):
        return NEO_NAMESPACE
    return DEFAULT_NAMESPACE


def usable_workflow_items(
    retrieval: dict[str, Any],
    assessment: dict[str, Any],
) -> list[dict[str, Any]]:
    chunks_by_id = {
        chunk.get("chunk_id"): chunk
        for chunk in retrieval.get("chunks", [])
        if isinstance(chunk, dict) and chunk.get("chunk_id")
    }
    items: list[dict[str, Any]] = []
    for source_assessment in assessment.get("source_assessments", []):
        if not isinstance(source_assessment, dict):
            continue
        label = str(source_assessment.get("relevance_label", "")).strip().lower()
        if label not in USABLE_RELEVANCE_LABELS:
            continue
        chunk = chunks_by_id.get(source_assessment.get("chunk_id"))
        if not isinstance(chunk, dict) or not chunk_is_safe_for_internal_answer(chunk):
            continue
        items.append(
            {
                "chunk": chunk,
                "assessment": source_assessment,
                "retrieval_schema_version": retrieval.get("schema_version"),
                "assessment_schema_version": assessment.get("schema_version"),
            }
        )
    return items


def chunk_is_safe_for_internal_answer(chunk: dict[str, Any]) -> bool:
    required_text_fields = ("chunk_id", "document_id", "title", "chunk_text", "source_path", "citation_string")
    if any(not isinstance(chunk.get(field), str) or not chunk.get(field).strip() for field in required_text_fields):
        return False
    if chunk.get("share_with_external_llm") is not False:
        return False
    if chunk.get("train_allowed") is not False:
        return False
    allowed_uses = chunk.get("allowed_uses")
    if not isinstance(allowed_uses, list):
        return False
    return bool(INTERNAL_ALLOWED_USES.intersection(str(use) for use in allowed_uses))


def citation_for_workflow_item(item: dict[str, Any]) -> dict[str, Any]:
    chunk = item["chunk"]
    assessment = item["assessment"]
    readiness = {
        "retrieve_allowed": True,
        "citation_ready": bool(chunk.get("citation_ready", False)),
        "analyst_citation_ready": bool(chunk.get("analyst_citation_ready", False)),
        "user_facing_ready": bool(chunk.get("user_facing_ready", False)),
        "share_with_external_llm": False,
        "train_allowed": False,
    }
    return {
        "trace_type": "retrieval_package.v1",
        "manifest_id": str(chunk.get("chunk_id", "")),
        "chunk_id": str(chunk.get("chunk_id", "")),
        "document_id": str(chunk.get("document_id", "")),
        "title": str(chunk.get("title", "")),
        "citation": str(chunk.get("citation_string", "")),
        "citation_string": str(chunk.get("citation_string", "")),
        "path": str(chunk.get("source_path", "")),
        "source_path": str(chunk.get("source_path", "")),
        "family": str(chunk.get("source_family", "")),
        "source_family": str(chunk.get("source_family", "")),
        "type": "workflow_rag_chunk",
        "readiness": readiness,
        "allowed_uses": list(chunk.get("allowed_uses") or []),
        "namespace": str(chunk.get("namespace", "")),
        "retrieval_mode": str(chunk.get("retrieval_mode", "")),
        "run_id": str(chunk.get("run_id", "")),
        "cosine_distance": chunk.get("cosine_distance"),
        "relevance_label": str(assessment.get("relevance_label", "")),
        "relevance_score": assessment.get("relevance_score"),
        "retrieval_schema_version": str(item.get("retrieval_schema_version", "")),
        "assessment_schema_version": str(item.get("assessment_schema_version", "")),
        "requires_human_review": True,
        "caveat_flags": [
            "internal_student_prototype_only",
            "not_public_client_official_or_validated",
            "trace_only_not_export_or_training",
        ],
    }


def _int_from_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default
