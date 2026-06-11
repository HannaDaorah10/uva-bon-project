"""Question classification for the NatureDesk backend router.

The classifier asks the local Spark Ollama model to choose only the next
evidence route. It does not retrieve evidence and it does not generate answers.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib import error, request


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
BACKEND_PIPELINE_NOT_CONNECTED = "backend_pipeline_not_connected"

ROUTES = {"text_rag", "score_table", "map_raster", "refusal"}

CROWN_SURFACE_RE = re.compile(
    r"(crown\s+surface|crown\s+area|tree\s+crown\s+area|kroonoppervlakte|kroon\s+oppervlakte)",
    re.IGNORECASE,
)
THE_HAGUE_RE = re.compile(r"(the\s+hague|den\s+haag|'s-gravenhage|gemeente\s+den\s+haag|gm0518)", re.IGNORECASE)
YEAR_2021_RE = re.compile(r"(2021|end\s+of\s+2021|eind\s+van\s+2021)", re.IGNORECASE)

REFUSAL_REASONS = {
    "no_evidence",
    "out_of_scope",
    "policy_restricted",
    "live_data_not_allowed",
    "unsupported_causal_claim",
    "unsupported_claim",
    "classifier_unavailable",
    "invalid_question",
    "no_approved_evidence",
    "readiness_gate_blocked",
    "export_gate_required",
    "action_gate_required",
}

ROUTER_SYSTEM_PROMPT = """
You are the NatureDesk router classifier.

Classify one ecologist question into exactly one route:
- text_rag: BON documentation, EBV definitions, project context, or other frozen text evidence.
- score_table: small prepared score/indicator tables such as NDVI, SHI, SHS, trends, rows, cells, or exact values.
- map_raster: maps, rasters, GeoTIFF, GPKG, PNG map outputs, spatial layers, or requests needing visual/geospatial inspection.
- refusal: out of scope, no frozen evidence, legal/policy/high-stakes advice, live/current data, web/GBIF/API requests, unsupported causal or predictive claims.

Rules:
- Use only the architecture boundary. No live internet, GBIF, or external data during a question.
- Legal/policy advice must be refusal with refusalReason policy_restricted.
- Live/current/up-to-date data requests must be refusal with refusalReason live_data_not_allowed.
- Unsupported causal or predictive claims must be refusal with refusalReason unsupported_causal_claim.
- If the question cannot be grounded in the frozen evidence types, use refusal with refusalReason no_evidence or out_of_scope.

Return ONLY JSON with this exact schema:
{
  "route": "text_rag|score_table|map_raster|refusal",
  "refusalReason": "no_evidence|out_of_scope|policy_restricted|live_data_not_allowed|unsupported_causal_claim|null",
  "confidence": 0.0,
  "explanation": "short reason"
}
""".strip()


@dataclass(frozen=True)
class RouterDecision:
    route: str
    refusal_reason: str | None
    confidence: float
    explanation: str

    @property
    def refused(self) -> bool:
        return self.route == "refusal"

    def as_api_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "refusalReason": self.refusal_reason,
            "confidence": self.confidence,
        }


class RouterClassificationError(RuntimeError):
    """Raised when the local router model cannot provide a valid decision."""


def refusal_answer(refusal_reason: str | None) -> str:
    answers = {
        "out_of_scope": (
            "I can only help with biodiversity, conservation, nature data, "
            "and related NatureDesk evidence questions."
        ),
        "policy_restricted": (
            "I cannot help with that request because it is outside the safe-use "
            "boundaries for this service."
        ),
        "live_data_not_allowed": (
            "I cannot provide live or real-time data from this backend. Please use "
            "a verified live data source for current conditions."
        ),
        "unsupported_causal_claim": (
            "I cannot make that causal claim from the available backend evidence. "
            "It would need an appropriate study design and supporting sources."
        ),
        "no_evidence": (
            "I do not have enough grounded evidence or context to route this "
            "question reliably."
        ),
        "classifier_unavailable": (
            "I cannot classify this request because the local router model is not "
            "available."
        ),
        "invalid_question": "Please enter a question for the NatureDesk router.",
        "unsupported_claim": (
            "I cannot support that claim from the approved frozen evidence and "
            "safe-use gates for this service."
        ),
        "no_approved_evidence": (
            "No approved local frozen evidence is available for this request."
        ),
        "readiness_gate_blocked": (
            "The matching frozen evidence is missing required readiness metadata "
            "or has a closed readiness gate."
        ),
        "export_gate_required": (
            "I cannot export, archive, attach, or bundle evidence from this route "
            "without a separate approved export gate."
        ),
        "action_gate_required": (
            "I cannot update, install, restart, mutate, or rerun services, "
            "databases, vectors, gates, or pipelines from this route."
        ),
    }
    return answers.get(refusal_reason or "no_evidence", answers["no_evidence"])


def classify_question(question: str) -> RouterDecision:
    clean_question = question.strip()
    if not clean_question:
        return RouterDecision(
            route="refusal",
            refusal_reason="invalid_question",
            confidence=1.0,
            explanation="The question is empty.",
        )

    heuristic = heuristic_decision(clean_question)
    if heuristic is not None:
        return heuristic

    try:
        payload = _call_ollama(clean_question)
        return parse_router_decision(payload)
    except Exception as exc:
        return RouterDecision(
            route="refusal",
            refusal_reason="classifier_unavailable",
            confidence=0.0,
            explanation=f"Router classifier unavailable: {exc.__class__.__name__}",
        )


def heuristic_decision(question: str) -> RouterDecision | None:
    if (
        CROWN_SURFACE_RE.search(question)
        and THE_HAGUE_RE.search(question)
        and YEAR_2021_RE.search(question)
    ):
        return RouterDecision(
            route="score_table",
            refusal_reason=None,
            confidence=0.98,
            explanation="Heuristic route for The Hague crown surface area question.",
        )
    return None


def _call_ollama(question: str) -> dict[str, Any]:
    prompt = f"{ROUTER_SYSTEM_PROMPT}\n\nQuestion: {question}"
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    req = request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RouterClassificationError(str(exc)) from exc

    model_text = raw.get("response")
    if not isinstance(model_text, str):
        raise RouterClassificationError("Ollama response did not include text")
    return extract_json_object(model_text)


def extract_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise RouterClassificationError("No JSON object found in classifier output")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise RouterClassificationError("Classifier output was not a JSON object")
    return value


def parse_router_decision(payload: dict[str, Any]) -> RouterDecision:
    route = str(payload.get("route", "")).strip()
    if route not in ROUTES:
        raise RouterClassificationError(f"Unknown route: {route}")

    raw_reason = payload.get("refusalReason")
    refusal_reason = None if raw_reason in {None, "null", ""} else str(raw_reason).strip()

    if route == "refusal":
        if refusal_reason not in REFUSAL_REASONS:
            refusal_reason = "no_evidence"
    else:
        refusal_reason = None

    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    explanation = payload.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        explanation = "Router selected this route from the local classifier."

    return RouterDecision(
        route=route,
        refusal_reason=refusal_reason,
        confidence=confidence,
        explanation=explanation.strip()[:500],
    )
