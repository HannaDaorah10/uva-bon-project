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
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request

from frozen_evidence import EvidenceGateResult
from handlers import HandlerResponse, safe_refusal
from router_classifier import DEFAULT_LOCAL_LLM_MODEL, validate_local_llm_model
from synthesis import synthesize_workflow_answer


DEFAULT_WORKFLOW_PATH = "/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py"
DEFAULT_NAMESPACE = "student_combined_baseline"
DEFAULT_TOP_K = 5
DEFAULT_TIMEOUT_SECONDS = 75
QUERY_UNDERSTANDING_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
QUERY_UNDERSTANDING_OLLAMA_MODEL = DEFAULT_LOCAL_LLM_MODEL
QUERY_UNDERSTANDING_TIMEOUT_SECONDS = 8
QUERY_UNDERSTANDING_MIN_CONFIDENCE = 0.65
NEO_NAMESPACE = "neo_den_haag_student_baseline"
NEO_TOP_K = 8
NEO_QUERY_TERMS = ("neo", "signaleyes", "signal eyes", "boombasis")
THE_HAGUE_OVERVIEW_QUERY = (
    "Den Haag The Hague Kroonvolume Groenmonitor NEO Boombasis urban biodiversity "
    "tree canopy evidence overview source holdings caveats"
)
PLACE_ALIASES = {
    "the_hague": (
        "the hague",
        "den haag",
        "'s-gravenhage",
        "s-gravenhage",
        "gemeente den haag",
        "gm0518",
    )
}
PLACE_CANONICAL_QUERIES = {
    "the_hague": THE_HAGUE_OVERVIEW_QUERY,
}
INVENTORY_TERMS = {
    "anything",
    "available",
    "contain",
    "contains",
    "data",
    "docs",
    "documents",
    "evidence",
    "have",
    "hold",
    "holdings",
    "info",
    "information",
    "know",
    "material",
    "file",
    "files",
    "overview",
    "records",
    "source",
    "sources",
    "summarize",
    "summary",
    "tell",
}
QUESTION_FILLER_TERMS = {
    "about",
    "any",
    "can",
    "could",
    "do",
    "does",
    "for",
    "give",
    "got",
    "have",
    "me",
    "of",
    "on",
    "please",
    "show",
    "tell",
    "the",
    "there",
    "to",
    "we",
    "what",
    "which",
    "you",
}
NARROW_REQUEST_TERMS = {
    "area",
    "export",
    "official",
    "proof",
    "restart",
    "validated",
}
LLM_UNDERSTANDING_BLOCK_TERMS = {
    "current",
    "live",
    "mayor",
    "policy",
    "safe",
    "safety",
    "today",
    "weather",
}
LLM_AMBIGUOUS_INVENTORY_TERMS = {
    "hebben",
    "heeft",
    "lokaal",
    "over",
    "re",
    "wat",
}
USABLE_RELEVANCE_LABELS = {"strong", "moderate", "usable", "partial"}
INTERNAL_ALLOWED_USES = {
    "internal_student_prototype_retrieval_assessment",
    "internal_student_challenge",
    "internal_research_prototype",
    "analyst_review",
}


@dataclass(frozen=True)
class QueryUnderstanding:
    intent: str
    place_key: str | None
    canonical_query: str | None = None


class QueryUnderstandingError(RuntimeError):
    """Raised when local query-understanding output is unavailable or invalid."""


QUERY_UNDERSTANDING_SYSTEM_PROMPT = """
You are a local NatureDesk query-understanding component.

Task: classify whether a user is asking what approved local evidence holdings
exist for a known place. Do not answer the question. Do not retrieve evidence.
Do not write citations. Do not create a custom search query.

Known place keys:
- the_hague: The Hague, Den Haag, 's-Gravenhage, gemeente Den Haag, GM0518

Return ONLY JSON with this exact schema:
{
  "intent": "place_inventory|literal_retrieval",
  "placeKey": "the_hague|null",
  "confidence": 0.0,
  "reason": "short reason"
}

Rules:
- Use place_inventory only for broad questions asking what information, data,
  evidence, files, records, sources, holdings, or material NatureDesk has about
  the known place.
- Use literal_retrieval for weather, mayor, safety, legal, policy, live/current,
  exact metric, proof, official-validation, export, restart, or action requests.
- The JSON is only an intent hint. It is not evidence.
""".strip()


def handle_workflow_rag(
    question: str,
    gate: EvidenceGateResult,
    model: str | None = None,
) -> HandlerResponse:
    if gate.refused:
        return safe_refusal(
            gate.refusal_reason or "readiness_gate_blocked",
            gate.answer or "The retrieval contract gate refused this request.",
        )

    fallback_refusal: HandlerResponse | None = None
    selected_model = validate_local_llm_model(model)
    for retrieval_question in retrieval_questions_for_user_question(question, model=selected_model):
        result = handle_single_retrieval_question(question, retrieval_question)
        if not result.refused:
            return result
        fallback_refusal = result
        if result.refusal_reason != "insufficient_evidence":
            return result

    return fallback_refusal or safe_refusal(
        "insufficient_evidence",
        "The controlled retrieval workflow did not find enough strong or moderate evidence.",
    )


def handle_single_retrieval_question(question: str, retrieval_question: str) -> HandlerResponse:
    payload, failure = run_diver_curator_workflow(retrieval_question)
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


def retrieval_question_for_user_question(question: str, model: str | None = None) -> str:
    """Return the first canonical retrieval query for backward-compatible callers."""
    return retrieval_questions_for_user_question(question, model=model)[0]


def retrieval_questions_for_user_question(question: str, model: str | None = None) -> list[str]:
    """Build a retrieval plan from understood intent instead of raw wording only."""
    understanding = understand_user_question(question, model=model)
    candidates: list[str] = []
    if understanding.canonical_query:
        candidates.append(understanding.canonical_query)
    candidates.append(question)
    return dedupe_preserving_order(candidates)


def understand_user_question(question: str, model: str | None = None) -> QueryUnderstanding:
    deterministic = understand_user_question_deterministic(question)
    if deterministic.canonical_query:
        return deterministic
    llm_understanding = understand_user_question_with_local_llm(
        question,
        deterministic,
        model=model,
    )
    return llm_understanding or deterministic


def understand_user_question_deterministic(question: str) -> QueryUnderstanding:
    place_key = detect_place_key(question)
    if place_key and looks_like_place_inventory_request(question, place_key):
        return QueryUnderstanding(
            intent="place_inventory",
            place_key=place_key,
            canonical_query=PLACE_CANONICAL_QUERIES[place_key],
        )
    return QueryUnderstanding(intent="literal_retrieval", place_key=place_key)


def understand_user_question_with_local_llm(
    question: str,
    deterministic: QueryUnderstanding,
    model: str | None = None,
) -> QueryUnderstanding | None:
    if os.environ.get("NATUREDESK_QUERY_UNDERSTANDING_LLM", "1").strip().lower() in {"0", "false", "no"}:
        return None
    if not should_try_local_llm_understanding(question, deterministic):
        return None
    try:
        payload = call_query_understanding_llm(question, model=model)
        return parse_query_understanding_payload(payload)
    except Exception:
        return None


def should_try_local_llm_understanding(question: str, deterministic: QueryUnderstanding) -> bool:
    if deterministic.place_key is None:
        return False
    terms = normalized_terms(question)
    if terms & (NARROW_REQUEST_TERMS | LLM_UNDERSTANDING_BLOCK_TERMS):
        return False
    remaining = terms - place_terms(deterministic.place_key) - QUESTION_FILLER_TERMS - INVENTORY_TERMS
    if remaining and not remaining <= LLM_AMBIGUOUS_INVENTORY_TERMS:
        return False
    return len(terms) >= 4


def call_query_understanding_llm(question: str, model: str | None = None) -> dict[str, Any]:
    url = os.environ.get("NATUREDESK_QUERY_UNDERSTANDING_OLLAMA_URL", QUERY_UNDERSTANDING_OLLAMA_URL)
    env_model = os.environ.get("NATUREDESK_QUERY_UNDERSTANDING_MODEL")
    selected_model = validate_local_llm_model(model or env_model or QUERY_UNDERSTANDING_OLLAMA_MODEL)
    timeout_seconds = _int_from_env(
        "NATUREDESK_QUERY_UNDERSTANDING_TIMEOUT_SECONDS",
        QUERY_UNDERSTANDING_TIMEOUT_SECONDS,
    )
    prompt = f"{QUERY_UNDERSTANDING_SYSTEM_PROMPT}\n\nQuestion: {question}"
    body = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    req = request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        raise QueryUnderstandingError(str(exc)) from exc

    model_text = raw.get("response")
    if not isinstance(model_text, str):
        raise QueryUnderstandingError("Ollama response did not include text")
    return extract_json_object(model_text)


def parse_query_understanding_payload(payload: dict[str, Any]) -> QueryUnderstanding | None:
    intent = str(payload.get("intent", "")).strip().lower()
    place_key = payload.get("placeKey", payload.get("place_key"))
    place_key = None if place_key in {None, "null", ""} else str(place_key).strip().lower()
    confidence = parse_confidence(payload.get("confidence"))

    if intent != "place_inventory":
        return None
    if place_key not in PLACE_CANONICAL_QUERIES:
        return None
    if confidence < QUERY_UNDERSTANDING_MIN_CONFIDENCE:
        return None
    return QueryUnderstanding(
        intent="place_inventory",
        place_key=place_key,
        canonical_query=PLACE_CANONICAL_QUERIES[place_key],
    )


def parse_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def extract_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise QueryUnderstandingError("No JSON object found in query-understanding output")
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise QueryUnderstandingError("Query-understanding output was not a JSON object")
    return value


def detect_place_key(question: str) -> str | None:
    normalized = normalize_for_matching(question)
    for place_key, aliases in PLACE_ALIASES.items():
        if any(normalize_for_matching(alias) in normalized for alias in aliases):
            return place_key
    return None


def looks_like_place_inventory_request(question: str, place_key: str) -> bool:
    terms = normalized_terms(question)
    if terms & NARROW_REQUEST_TERMS:
        return False
    remaining = terms - place_terms(place_key) - QUESTION_FILLER_TERMS
    if remaining and remaining <= INVENTORY_TERMS:
        return True
    if terms & INVENTORY_TERMS and not remaining:
        return True
    return not remaining


def place_terms(place_key: str) -> set[str]:
    terms: set[str] = set()
    for alias in PLACE_ALIASES[place_key]:
        terms.update(normalized_terms(alias))
    return terms


def normalized_terms(text: str) -> set[str]:
    return {
        part
        for part in normalize_for_matching(text).split()
        if len(part) > 1
    }


def normalize_for_matching(text: str) -> str:
    cleaned = []
    for char in text.lower():
        cleaned.append(char if char.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


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
