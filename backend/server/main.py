"""HTTP API for the NatureDesk backend router."""

from typing import Any, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from citation_validator import citations_are_valid
from frozen_evidence import EvidenceGateResult, gate_query_evidence, preflight_question_gate
from handlers import HandlerResponse
from handlers.map_raster import handle_map_raster
from handlers.score_table_dynamic import handle_score_table
from handlers.text_rag import handle_text_rag
from handlers.workflow_rag import handle_workflow_rag
from router_classifier import (
    BACKEND_PIPELINE_NOT_CONNECTED,
    DEFAULT_LOCAL_LLM_MODEL,
    InvalidLocalModelError,
    RouterDecision,
    classify_question,
    refusal_answer,
    validate_local_llm_model,
)


app = FastAPI(title="NatureDesk Backend API")

HANDLERS = {
    "score_table": handle_score_table,
    "text_rag": handle_text_rag,
    "workflow_rag": handle_workflow_rag,
    "map_raster": handle_map_raster,
}


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    model: Optional[str] = Field(default=DEFAULT_LOCAL_LLM_MODEL)


class QueryResponse(BaseModel):
    refused: bool
    answer: str
    citations: List[Any]
    refusalReason: Optional[str] = None
    router: Optional[dict[str, Any]] = None
    evidence: Optional[dict[str, Any]] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse, response_model_exclude_none=True)
def query(request: QueryRequest) -> QueryResponse:
    preflight_refusal = preflight_question_gate(request.question)
    if preflight_refusal is not None:
        return refusal_response(
            RouterDecision(
                route="refusal",
                refusal_reason=preflight_refusal.refusal_reason,
                confidence=1.0,
                explanation="Frozen evidence preflight gate refused the request.",
            ),
            answer=preflight_refusal.answer,
            refusal_reason=preflight_refusal.refusal_reason,
            evidence_gate=preflight_refusal,
        )

    try:
        selected_model = validate_local_llm_model(getattr(request, "model", DEFAULT_LOCAL_LLM_MODEL))
    except InvalidLocalModelError:
        return refusal_response(
            RouterDecision(
                route="refusal",
                refusal_reason="invalid_model",
                confidence=1.0,
                explanation="Requested local model is outside the backend allowlist.",
            ),
            answer=refusal_answer("invalid_model"),
            refusal_reason="invalid_model",
        )

    decision = classify_question(request.question, model=selected_model)
    if decision.refused:
        return refusal_response(
            decision,
            answer=refusal_answer(decision.refusal_reason),
        )

    evidence_gate = gate_query_evidence(decision.route)
    if evidence_gate.refused:
        return refusal_response(
            decision,
            answer=evidence_gate.answer,
            refusal_reason=evidence_gate.refusal_reason,
            evidence_gate=evidence_gate,
        )

    handler = HANDLERS.get(decision.route)
    if handler is None:
        return refusal_response(
            decision,
            answer="This query type is not supported by the demo handlers.",
            refusal_reason=BACKEND_PIPELINE_NOT_CONNECTED,
            evidence_gate=evidence_gate,
        )

    if decision.route == "workflow_rag":
        result = handler(request.question, evidence_gate, model=selected_model)
    else:
        result = handler(request.question, evidence_gate)
    if result.refused:
        return handler_refusal_response(decision, result, evidence_gate)

    if not citations_are_valid(result.citations):
        return refusal_response(
            decision,
            answer=(
                "The demo handler produced an answer without valid frozen-evidence "
                "citations, so the response was refused."
            ),
            refusal_reason="citation_validation_failed",
            evidence_gate=evidence_gate,
        )

    return answer_response(decision, result, evidence_gate)


def refusal_response(
    decision: RouterDecision,
    answer: str,
    refusal_reason: str | None = None,
    evidence_gate: EvidenceGateResult | None = None,
) -> QueryResponse:
    router = decision.as_api_dict()
    if evidence_gate is not None and evidence_gate.evidence_family:
        router["evidence_family"] = evidence_gate.evidence_family

    return QueryResponse(
        refused=True,
        answer=answer,
        citations=[],
        refusalReason=refusal_reason or decision.refusal_reason,
        router=router,
        evidence=evidence_gate.as_api_dict() if evidence_gate is not None else None,
    )


def handler_refusal_response(
    decision: RouterDecision,
    result: HandlerResponse,
    evidence_gate: EvidenceGateResult,
) -> QueryResponse:
    return refusal_response(
        decision,
        answer=result.answer,
        refusal_reason=result.refusal_reason,
        evidence_gate=evidence_gate,
    )


def answer_response(
    decision: RouterDecision,
    result: HandlerResponse,
    evidence_gate: EvidenceGateResult,
) -> QueryResponse:
    router = decision.as_api_dict()
    if evidence_gate.evidence_family:
        router["evidence_family"] = evidence_gate.evidence_family

    return QueryResponse(
        refused=False,
        answer=result.answer,
        citations=result.citations,
        refusalReason=None,
        router=router,
        evidence=evidence_gate.as_api_dict(),
    )
