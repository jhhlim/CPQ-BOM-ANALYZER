import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import IngestRequest, IngestResponse, AnalyzeRequest, AnalyzeResponse
from app.config import settings
from app.models import Document, Chunk

from app.rag.ingest import ingest_folder
from app.rag.bom_parser import parse_bom_text
from app.rag.analyze import embed_texts, embed_query, generate_report
from app.rag.retrieve import retrieve_chunks
from app.utils.text_splitter import ChunkConfig

app = FastAPI(title="Quote/BOM Risk Analyzer (RAG)")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest, db: Session = Depends(get_db)):
    if not os.path.isdir(req.path):
        raise HTTPException(status_code=400, detail=f"Path not found or not a directory: {req.path}")

    cfg = ChunkConfig(chunk_chars=settings.CHUNK_CHARS, overlap=settings.CHUNK_OVERLAP)

    try:
        docs_added, docs_skipped, chunks_added = ingest_folder(
            db=db,
            folder_path=req.path,
            embed_fn=embed_texts,
            product_line=req.product_line,
            region=req.region,
            doc_type=req.doc_type,
            effective_date=req.effective_date,
            chunk_cfg=cfg,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

    return IngestResponse(
        documents_added=docs_added,
        documents_skipped=docs_skipped,
        chunks_added=chunks_added,
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    bom_text = req.bom_text.strip()
    parsed = parse_bom_text(bom_text)

    top_k = req.top_k or settings.TOP_K

    # Build retrieval query text (simple but effective)
    query_text = bom_text[:4000]
    if parsed["part_numbers"]:
        query_text += "\n\nPart numbers:\n" + "\n".join(parsed["part_numbers"][:50])
    if parsed["keywords"]:
        query_text += "\n\nKeywords:\n" + ", ".join(parsed["keywords"][:50])

    try:
        q_emb = embed_query(query_text)
        retrieved = retrieve_chunks(
            db=db,
            query_embedding=q_emb,
            top_k=top_k,
            product_line=req.product_line,
            region=req.region,
        )
        if not retrieved:
            raise HTTPException(status_code=404, detail="No documents/chunks retrieved. Ingest docs first.")

        report = generate_report(
            bom_text=bom_text,
            parsed=parsed,
            retrieved=retrieved,
            product_line=req.product_line,
            region=req.region,
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")

@app.get("/sources/{doc_id}")
def sources(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc.id)
        .order_by(Chunk.chunk_index.asc())
        .all()
    )

    return {
        "doc_id": str(doc.id),
        "title": doc.title,
        "source_path": doc.source_path,
        "doc_type": doc.doc_type,
        "product_line": doc.product_line,
        "region": doc.region,
        "effective_date": str(doc.effective_date) if doc.effective_date else None,
        "chunks": [
            {
                "chunk_id": str(c.id),
                "chunk_index": c.chunk_index,
                "text": c.text,
                "metadata": c.metadata_,
            }
            for c in chunks
        ],
    }