"""
parse_profile.py — turn a raw candidate file (.txt/.docx/.pdf) into a structured
CandidateProfile of signals the scorer can use.

Phase 0 is fully deterministic (regex + lexicons). Phase 1 can swap in / augment
this with LLM parsing + enrichment via enrich.py, keeping the same output shape.
"""

from __future__ import annotations
import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CandidateProfile:
    name: str
    raw_text: str
    location: str | None = None
    languages: list[str] = field(default_factory=list)
    years_experience: float | None = None
    distinctions: list[str] = field(default_factory=list)
    open_to_work_signals: list[str] = field(default_factory=list)
    relocation_signals: list[str] = field(default_factory=list)
    # Provenance: which fields were explicitly found vs. inferred/absent.
    provenance: dict = field(default_factory=dict)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(path: str | Path) -> str:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".docx":
        import docx  # python-docx
        return "\n".join(p.text for p in docx.Document(str(path)).paragraphs)
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    raise ValueError(f"Unsupported file type: {ext} (use .txt, .docx, or .pdf)")


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_regex(text: str, patterns: list[str]) -> list[str]:
    """Return the distinct lexicon patterns that match (case-insensitive)."""
    hits = []
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            hits.append(m.group(0))
    return hits


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return "Unknown candidate"


def _extract_location(text: str) -> str | None:
    m = re.search(r"location\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extract_languages(text: str) -> list[str]:
    m = re.search(r"languages?\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if not m:
        return []
    # Split on commas / semicolons; keep "French (native)" style intact.
    return [p.strip() for p in re.split(r"[;,]", m.group(1)) if p.strip()]


def _extract_years(text: str) -> float | None:
    years = [int(x) for x in re.findall(r"(\d{1,2})\+?\s+years", text, re.IGNORECASE)]
    return float(max(years)) if years else None


# ── Main entry ────────────────────────────────────────────────────────────────

def parse_candidate(path: str | Path, lexicons: dict) -> CandidateProfile:
    text = extract_text(path)

    name = _first_nonempty_line(text)
    location = _extract_location(text)
    languages = _extract_languages(text)
    years = _extract_years(text)
    # Distinctions span awards + domain authority + publications/patents lexicons.
    distinctions = find_regex(text, (lexicons.get("awards", []) +
                                     lexicons.get("authority", []) +
                                     lexicons.get("publications", [])))
    open_signals = find_regex(text, lexicons.get("open_to_work", []))
    # Mobility signals span relocation interest + travel willingness.
    reloc_signals = find_regex(text, (lexicons.get("interest_relocation", []) +
                                      lexicons.get("willingness_travel", [])))

    provenance = {
        "location": "explicit" if location else "absent",
        "languages": "explicit" if languages else "absent",
        "years_experience": "explicit" if years is not None else "absent",
        "distinctions": "explicit" if distinctions else "absent",
        "open_to_work": "explicit" if open_signals else "absent",
        "relocation": "explicit" if reloc_signals else "absent",
    }

    return CandidateProfile(
        name=name,
        raw_text=text,
        location=location,
        languages=languages,
        years_experience=years,
        distinctions=distinctions,
        open_to_work_signals=open_signals,
        relocation_signals=reloc_signals,
        provenance=provenance,
    )
