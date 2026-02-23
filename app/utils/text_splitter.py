from dataclasses import dataclass

@dataclass
class ChunkConfig:
    chunk_chars: int = 1800
    overlap: int = 250

def chunk_text(text: str, cfg: ChunkConfig) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    chunks = []
    i = 0
    n = len(text)

    while i < n:
        end = min(i + cfg.chunk_chars, n)
        chunk = text[i:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        i = max(0, end - cfg.overlap)

    return chunks