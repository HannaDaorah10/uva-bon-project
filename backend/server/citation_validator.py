"""Minimal citation checks for demo handler responses."""

from __future__ import annotations

from typing import Any


REQUIRED_CITATION_FIELDS = {"manifest_id", "citation", "path", "family", "type"}
REQUIRED_RETRIEVAL_TRACE_FIELDS = {
    "chunk_id",
    "document_id",
    "title",
    "citation_string",
    "source_path",
    "source_family",
    "namespace",
    "retrieval_mode",
    "relevance_label",
    "retrieval_schema_version",
    "assessment_schema_version",
}
USABLE_RELEVANCE_LABELS = {"strong", "moderate", "usable", "partial"}
INTERNAL_ALLOWED_USES = {
    "internal_student_prototype_retrieval_assessment",
    "internal_student_challenge",
    "internal_research_prototype",
    "analyst_review",
}


def citations_are_valid(citations: list[Any]) -> bool:
    if not citations:
        return False
    return all(is_valid_citation(citation) for citation in citations)


def is_valid_citation(citation: Any) -> bool:
    if is_valid_retrieval_contract_citation(citation):
        return True
    return is_valid_frozen_manifest_citation(citation)


def is_valid_frozen_manifest_citation(citation: Any) -> bool:
    if not isinstance(citation, dict):
        return False
    for field_name in REQUIRED_CITATION_FIELDS:
        value = citation.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return False

    readiness = citation.get("readiness")
    if not isinstance(readiness, dict):
        return False
    if readiness.get("retrieve_allowed") is not True:
        return False
    if readiness.get("quote_allowed") is not True:
        return False
    if readiness.get("export_allowed") is not False:
        return False
    if readiness.get("share_external_llm_allowed") is not False:
        return False
    if readiness.get("train_allowed") is not False:
        return False
    if readiness.get("citation_ready") is not True:
        return False
    if readiness.get("user_facing_ready") is not True:
        return False

    return True


def is_valid_retrieval_contract_citation(citation: Any) -> bool:
    if not isinstance(citation, dict):
        return False
    if citation.get("trace_type") != "retrieval_package.v1":
        return False
    for field_name in REQUIRED_RETRIEVAL_TRACE_FIELDS:
        value = citation.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return False

    if citation.get("retrieval_schema_version") != "retrieval_package.v1":
        return False
    if citation.get("assessment_schema_version") != "source_assessment.v1":
        return False
    if str(citation.get("relevance_label", "")).strip().lower() not in USABLE_RELEVANCE_LABELS:
        return False
    if not _is_number(citation.get("cosine_distance")):
        return False

    allowed_uses = citation.get("allowed_uses")
    if not isinstance(allowed_uses, list):
        return False
    if not INTERNAL_ALLOWED_USES.intersection(str(value) for value in allowed_uses):
        return False

    readiness = citation.get("readiness")
    if not isinstance(readiness, dict):
        return False
    if readiness.get("retrieve_allowed") is not True:
        return False
    if readiness.get("share_with_external_llm") is not False:
        return False
    if readiness.get("train_allowed") is not False:
        return False
    return True


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
