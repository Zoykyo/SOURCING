"""
enrich.py — OPTIONAL LLM enrichment layer ("the unspoken" model).

Phase 0 runs fully without this. When an ANTHROPIC_API_KEY is present and
--enrich is passed, this uses Claude to (a) parse messy resume text into the
same signal fields more robustly, and (b) infer likely-but-unstated attributes
(seniority, domain adjacency, probable openness) — ALWAYS tagged with a
confidence score and marked as inferred, never silently treated as fact.

This is a stub interface for Phase 1; the deterministic engine is the default.
"""

from __future__ import annotations
import os

from parse_profile import CandidateProfile

MODEL = "claude-sonnet-4-6"  # cheap/fast for bulk parsing; opus for hard cases


def is_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def enrich_profile(cand: CandidateProfile, role: dict) -> CandidateProfile:
    """
    Augment a deterministically-parsed profile with LLM-inferred signals.
    Returns the candidate unchanged if no API key is configured.

    TODO (Phase 1): call the Anthropic API with a structured-output schema that
    returns {field, value, confidence, source} records, merge only fields that
    are currently absent, and store provenance = 'inferred' + confidence.
    """
    if not is_available():
        return cand
    # Placeholder — wired up in Phase 1 once the API key + schema are in place.
    return cand
