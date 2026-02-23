from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Chunk, Document

def retrieve_chunks(
    db: Session,
    query_embedding: list[float],
    top_k: int,
    product_line: str | None = None,
    region: str | None = None,
) -> list[tuple[Chunk, Document, float]]:
    """
    Returns list of (chunk, doc, distance)
    """
    # cosine distance operator provided by pgvector SQLAlchemy type
    distance = Chunk.embedding.cosine_distance(query_embedding)

    stmt = (
        select(Chunk, Document, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
    )

    if product_line:
        stmt = stmt.where(Document.product_line == product_line)
    if region:
        stmt = stmt.where(Document.region == region)

    stmt = stmt.order_by(distance.asc()).limit(top_k)

    rows = db.execute(stmt).all()
    return [(r[0], r[1], float(r[2])) for r in rows]