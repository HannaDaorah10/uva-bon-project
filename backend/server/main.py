"""HTTP API for the NatureDesk backend router."""

from typing import Any, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse, response_model_exclude_none=True)
def query(request: QueryRequest) -> QueryResponse:
    decision = classify_question(request.question)
    if decision.refused:
        return refusal_response(
            decision,
            answer=refusal_answer(decision.refusal_reason),
        )

    return refusal_response(
        decision,
        answer=(
            "The router classified this question, but retrieval and synthesis "
            "are not connected to the HTTP API yet."
        ),
        refusal_reason=BACKEND_PIPELINE_NOT_CONNECTED,
    )


def refusal_response(
    decision: RouterDecision,
    answer: str,
    refusal_reason: str | None = None,
) -> QueryResponse:
    return QueryResponse(
        refused=True,
        answer=answer,
        citations=[],
        refusalReason=refusal_reason or decision.refusal_reason,
        router=decision.as_api_dict(),
    )
