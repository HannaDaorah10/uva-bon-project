"""Minimal citation checks for demo handler responses."""

from __future__ import annotations

from typing import Any


REQUIRED_CITATION_FIELDS = {"manifest_id", "citation", "path", "family", "type"}


def citations_are_valid(citations: list[Any]) -> bool:
    if not citations:
        return False
    return all(is_valid_citation(citation) for citation in citations)


def is_valid_citation(citation: Any) -> bool:
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
    if readiness.get("export_allowed") is not False:
        return False
    if readiness.get("share_external_llm_allowed") is not False:
        return False
    if readiness.get("train_allowed") is not False:
        return False
    
    return True
