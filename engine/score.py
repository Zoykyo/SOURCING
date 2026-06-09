"""
score.py — Phase 0 CLI for the SOURCING find-and-rank engine.

Score one candidate against a role, or rank a whole folder of candidates.

Examples
--------
  # Single candidate -> Markdown scorecard
  python score.py --role roles/role_mechanical_engineer.yaml \
                  --candidate candidates/marie_tremblay.txt

  # Rank a folder -> Excel shortlist + a scorecard per candidate
  python score.py --role roles/role_mechanical_engineer.yaml \
                  --candidates-dir candidates/

Runs fully offline (deterministic). Pass --enrich to use Claude enrichment
when an ANTHROPIC_API_KEY is set (Phase 1).
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Windows consoles default to cp1252; force UTF-8 so emoji/accents don't crash prints.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import yaml

from parse_profile import parse_candidate
from scoring import score_candidate
from report import write_markdown, write_shortlist_xlsx
import enrich
import reference as ref_lib

HERE = Path(__file__).parent
SUPPORTED = {".txt", ".docx", ".pdf"}


def load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def gather_candidates(args) -> list[Path]:
    if args.candidate:
        return [Path(args.candidate)]
    d = Path(args.candidates_dir)
    return sorted(p for p in d.iterdir() if p.suffix.lower() in SUPPORTED)


def main(argv=None):
    ap = argparse.ArgumentParser(description="SOURCING — find & rank engine (Phase 0)")
    ap.add_argument("--role", required=True, help="Path to role YAML")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--candidate", help="Path to a single candidate file")
    g.add_argument("--candidates-dir", help="Folder of candidate files to rank")
    ap.add_argument("--model", default=str(HERE / "model.yaml"), help="Scoring model YAML")
    ap.add_argument("--reference", default=str(ref_lib.DEFAULT_PATH), help="Target-employers reference YAML")
    ap.add_argument("--out", default=str(HERE / "reports"), help="Output directory")
    ap.add_argument("--enrich", action="store_true", help="Use LLM enrichment if available")
    args = ap.parse_args(argv)

    model = load_yaml(args.model)
    role = load_yaml(args.role)
    reference = ref_lib.load_reference(args.reference)
    lex = model["lexicons"]

    if args.enrich and not enrich.is_available():
        print("⚠️  --enrich requested but ANTHROPIC_API_KEY not set; running deterministic.",
              file=sys.stderr)

    results = []
    for path in gather_candidates(args):
        cand = parse_candidate(path, lex)
        if args.enrich and enrich.is_available():
            cand = enrich.enrich_profile(cand, role)
        result = score_candidate(cand, role, model, reference)
        results.append(result)
        md = write_markdown(result, role, args.out)
        flag = " 🏆 WOW" if result["wow"] else ""
        if result["no_poach"]["triggered"]:
            flag += f"  ⛔ NO-POACH ({', '.join(result['no_poach']['companies'])})"
        print(f"  {result['total_score']:5.1f}  {result['status']:<38} "
              f"{result['candidate']}{flag}")
        print(f"         scorecard: {md}")

    if len(results) > 1:
        results.sort(key=lambda r: r["total_score"], reverse=True)
        xlsx = write_shortlist_xlsx(results, role, args.out)
        print(f"\n  Ranked shortlist ({len(results)} candidates): {xlsx}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
