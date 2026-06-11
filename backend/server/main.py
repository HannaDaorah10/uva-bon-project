"""HTTP API for the NatureDesk backend router."""

from typing import Any, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from frozen_evidence import EvidenceGateResult, gate_query_evidence, preflight_question_gate
from router_classifier import (
    BACKEND_PIPELINE_NOT_CONNECTED,
    RouterDecision,
    classify_question,
    refusal_answer,
)


app = FastAPI(title="NatureDesk Backend API")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


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

    decision = classify_question(request.question)
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

    return refusal_response(
        decision,
        answer=(
            "The router classified this question and found an approved frozen "
            "evidence route, but retrieval, citation validation, and synthesis "
            "are not connected to the HTTP API yet."
        ),
        refusal_reason=BACKEND_PIPELINE_NOT_CONNECTED,
        evidence_gate=evidence_gate,
    )


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
