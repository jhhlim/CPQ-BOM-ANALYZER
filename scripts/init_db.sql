CREATE EXTENSION IF NOT EXISTS vector;

-- Adjust dimension if you switch embedding models.
-- text-embedding-3-small is commonly 1536 dims.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
    RAISE EXCEPTION 'pgvector extension not installed properly.';
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  source_path TEXT NOT NULL,
  doc_type TEXT,
  product_line TEXT,
  region TEXT,
  effective_date DATE,
  content_hash TEXT UNIQUE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  text TEXT NOT NULL,
  embedding VECTOR(1536),
  char_count INT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_meta ON chunks USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
  ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);