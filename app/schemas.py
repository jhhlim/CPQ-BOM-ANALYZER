from pydantic import BaseModel, Field
from typing import Any, Literal

class IngestRequest(BaseModel):
    path: str
    product_line: str | None = None
    region: str | None = None
    doc_type: str | None = None
    effective_date: str | None = None  # YYYY-MM-DD

class IngestResponse(BaseModel):
    documents_added: int
    documents_skipped: int
    chunks_added: int

class AnalyzeRequest(BaseModel):
    bom_text: str = Field(min_length=1)
    product_line: str | None = None
    region: str | None = None
    top_k: int | None = None

Severity = Literal["low", "medium", "high"]

class Evidence(BaseModel):
    source_title: str
    doc_id: str
    chunk_id: str
    quote: str

class Finding(BaseModel):
    title: str
    severity: Severity
    description: str
    recommended_action: str
    evidence: list[Evidence]

class MissingPart(BaseModel):
    item: str
    reason: str
    evidence: list[Evidence]

class Upsell(BaseModel):
    item: str
    why: str
    evidence: list[Evidence]

class Approval(BaseModel):
    type: str
    trigger: str
    evidence: list[Evidence]

class RetrievalDiagnostics(BaseModel):
    top_sources: list[str]
    retrieved_chunk_ids: list[str]
    notes: str | None = None

class AnalyzeResponse(BaseModel):
    summary: str
    risks: list[Finding]
    missing_parts: list[MissingPart]
    suggested_upsells: list[Upsell]
    required_approvals: list[Approval]
    retrieval_diagnostics: RetrievalDiagnostics