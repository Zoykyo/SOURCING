"""
reference.py — load and query the target-employer / key-OEM reference list
(engine/reference/target_employers.yaml, parsed from Kollabtek's client deck).

Used for three things in scoring:
  1. Relevance boost  — sector auto-fill of a role's target employers.
  2. No-poach         — set of ACTIVE-CLIENT names (don't recruit away from clients).
  3. Sector lookup    — companies grouped by sector.
"""

from __future__ import annotations
from pathlib import Path
import yaml

DEFAULT_PATH = Path(__file__).parent / "reference" / "target_employers.yaml"


def load_reference(path: str | Path = DEFAULT_PATH) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def companies_for_sector(ref: dict | None, sector: str | None) -> list[str]:
    """All company names in a sector (client + prospect)."""
    if not ref or not sector:
        return []
    s = ref.get("sectors", {}).get(sector)
    return [c["name"] for c in s["companies"]] if s else []


def active_client_names(ref: dict | None) -> list[str]:
    """Names of ACTIVE clients across ALL sectors (no-poach applies firm-wide)."""
    if not ref:
        return []
    names = []
    for s in ref.get("sectors", {}).values():
        names += [c["name"] for c in s["companies"] if c.get("status") == "client"]
    return names


def sector_keys(ref: dict | None) -> list[str]:
    return list(ref.get("sectors", {}).keys()) if ref else []
