"""Minimal fail-closed HTTP API skeleton for the NatureDesk backend."""

from typing import Any, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="NatureDesk Backend API")


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    refused: bool
    answer: str
    citations: List[Any]
    refusalReason: Optional[str] = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/query", response_model=QueryResponse)
def query(_request: QueryRequest) -> QueryResponse:
    return QueryResponse(
        refused=True,
        answer="",
        citations=[],
        refusalReason="backend_pipeline_not_connected",
    )
