# SOURCING Engine — Phase 0 (Find & Rank)

A local, offline scoring engine that operationalizes Kollabtek's 5-category
Multi-Criteria Sourcing Model. Give it a **role** and one or more **candidate
files**; it returns ranked, **explainable** scorecards.

No API keys, no cloud, no LinkedIn access required. This is the core that
Phase 1 (LinkedIn Chrome capture + Zoho) plugs into.

## Install

```powershell
cd engine
python -m pip install -r requirements.txt
```

## Run

```powershell
# Single candidate -> Markdown scorecard
python score.py --role roles/role_mechanical_engineer.yaml --candidate candidates/marie_tremblay.txt

# Rank a whole folder -> Excel shortlist + a scorecard per candidate
python score.py --role roles/role_mechanical_engineer.yaml --candidates-dir candidates/
```

Outputs land in `engine/reports/`:
- `scorecard_<Name>.md` — per-candidate evidence breakdown
- `shortlist_<RoleId>.xlsx` — ranked comparison table

Candidate files may be `.txt`, `.docx`, or `.pdf`.

## How scoring works

1. **Parse** (`parse_profile.py`) — extract text + role-agnostic signals
   (distinctions, openness, mobility) deterministically.
2. **Score** (`scoring.py`) — apply the model: per-criterion 0-100 scores →
   weighted category scores → weighted total. Every score carries evidence and
   a provenance tag (`explicit` vs `no data → neutral`).
3. **Gate** — must-have skills are a hard filter; missing any flags the
   candidate *below bar* (still scored, recruiter can override).
4. **Wow** — flags rare high-value combos (all must-haves + high score +
   distinction + key OEM/standards), the "A+B+C = Wow!" idea.
5. **Report** (`report.py`) — Markdown scorecard + Excel shortlist.

## Tuning

- **`model.yaml`** — category & criteria weights, seniority bands, keyword
  lexicons, gate/Wow thresholds. Edit to retune scoring globally.
- **`roles/*.yaml`** — one per requisition: must-have/nice-to-have skills,
  target employers, standards, languages, region. May override category weights
  per role. In Phase 1 this auto-populates from a Zoho Recruit Job Opening.

## Optional LLM enrichment (Phase 1)

`enrich.py` is a stub for "the unspoken" model — using Claude to robustly parse
messy resumes and infer likely-but-unstated attributes, always tagged with
confidence and marked as inferred. Activated with `--enrich` once
`ANTHROPIC_API_KEY` is set. The engine runs fully without it.

## Target-employer reference & no-poach

`reference/target_employers.yaml` is Kollabtek's target client/OEM list (by sector,
province, and `status: client | prospect`). Set a `sector:` on a role and the engine:

- **Relevance boost** — auto-fills the role's target employers with that sector's
  companies, so candidates who worked at sector-relevant firms score higher
  (clients and prospects count equally). Scored on domain *relevance*, not prestige.
- **No-poach** — flags any candidate **currently employed at an active client**
  (firm-wide, any sector) — status becomes `⛔ No-poach` with a scorecard banner.
  Past employment at a client is NOT flagged (that's the relevance boost).

Regenerate the reference from an updated deck with the pptx parser, or edit the YAML
directly. No-poach detection is a heuristic (name on a line marked "present"); the
recruiter confirms before excluding.

## Layout

```
engine/
  model.yaml            scoring model (weights, thresholds, lexicons)
  score.py              CLI entry point
  parse_profile.py      file -> structured signals
  scoring.py            multi-criteria scoring engine
  reference.py          loads target_employers.yaml (sector fill + no-poach)
  enrich.py             optional LLM enrichment (Phase 1 stub)
  report.py             Markdown + Excel output
  roles/                per-requisition role configs (set `sector:`)
  candidates/           candidate files to score (sample data included)
  reference/            target-employer / key-OEM reference list
  reports/              generated scorecards & shortlists (output)
```
