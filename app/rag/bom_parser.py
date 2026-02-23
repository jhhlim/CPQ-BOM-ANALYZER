import re

PART_RE = re.compile(r"\b[A-Z0-9][A-Z0-9_-]{5,}\b")
QTY_RE = re.compile(r"(?i)\b(qty|quantity)\s*[:=]?\s*(\d+)\b|\b(\d+)\s*[xX]\b")

def parse_bom_text(bom_text: str) -> dict:
    text = bom_text or ""
    part_numbers = sorted(set(PART_RE.findall(text)))

    # naive qty mapping: finds qty near lines containing parts
    quantities = {}
    lines = text.splitlines()
    for line in lines:
        parts = PART_RE.findall(line)
        if not parts:
            continue
        qty = None
        m = QTY_RE.search(line)
        if m:
            qty = int(m.group(2) or m.group(3))
        for p in parts:
            if qty is not None:
                quantities[p] = qty
            else:
                quantities.setdefault(p, 1)

    # lightweight keyword extraction
    lower = text.lower()
    keywords = []
    for kw in ["object storage", "controller", "firmware", "cabling", "license", "support", "data protection", "backup", "nas", "throughput", "25g", "100g"]:
        if kw in lower:
            keywords.append(kw)

    return {
        "part_numbers": part_numbers,
        "quantities": quantities,
        "keywords": keywords,
    }