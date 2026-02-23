import json
from openai import OpenAI
from app.config import settings
from app.rag.prompts import SYSTEM_PROMPT, USER_TEMPLATE

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def embed_texts(texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,
        input=texts,
    )
    return [d.embedding for d in resp.data]

def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

def format_context_snippets(retrieved: list[tuple]) -> str:
    # retrieved: (chunk, doc, distance)
    blocks = []
    for chunk, doc, _dist in retrieved:
        blocks.append(
            f"- doc_title: {doc.title}\n"
            f"  doc_id: {str(doc.id)}\n"
            f"  chunk_id: {str(chunk.id)}\n"
            f"  text: {chunk.text}\n"
        )
    return "\n".join(blocks)

def chat_json(system_prompt: str, user_prompt: str) -> dict:
    # Enforce JSON response with OpenAI response_format if available.
    # We'll also do a strict JSON parse fallback.
    resp = client.chat.completions.create(
        model=settings.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    content = content.strip()

    # Try parse JSON strictly
    try:
        return json.loads(content)
    except Exception:
        # Attempt to recover if model wrapped JSON in text
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start:end+1])
        raise ValueError("Model did not return valid JSON.")

def generate_report(
    bom_text: str,
    parsed: dict,
    retrieved: list[tuple],
    product_line: str | None,
    region: str | None,
) -> dict:
    context_snips = format_context_snippets(retrieved)
    retrieved_chunk_ids = [str(ch.id) for ch, _doc, _d in retrieved]
    top_sources = list(dict.fromkeys([str(doc.id) for _ch, doc, _d in retrieved]))  # preserve order unique

    user_prompt = USER_TEMPLATE.format(
        bom_text=bom_text,
        part_numbers=parsed.get("part_numbers", []),
        keywords=parsed.get("keywords", []),
        quantities=parsed.get("quantities", {}),
        product_line=product_line,
        region=region,
        context_snippets=context_snips,
    )

    report = chat_json(SYSTEM_PROMPT, user_prompt)

    # Attach retrieval diagnostics if missing
    if "retrieval_diagnostics" not in report:
        report["retrieval_diagnostics"] = {}
    report["retrieval_diagnostics"].setdefault("top_sources", top_sources)
    report["retrieval_diagnostics"].setdefault("retrieved_chunk_ids", retrieved_chunk_ids)
    report["retrieval_diagnostics"].setdefault("notes", None)

    return report