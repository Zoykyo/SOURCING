# SOURCING

Smart sourcing tool to help Kollabtek recruiters **find, reach, and attract** top
technical candidates. It operationalizes Kollabtek's Multi-Criteria Sourcing Model
(5 categories × 5 sub-criteria) into a working, explainable candidate-scoring engine.

> **Status:** Phase 0 (Find & Rank) — a local, offline scoring engine. No cloud,
> no API keys, no LinkedIn access required to run.

## Repository layout

```
PROJECT_SCOPE.md          Full project scope, decisions, and phased roadmap
build_sourcing_model.py   Legacy generator for the original model workbook
KNOWLEDGE BASE/           Source model & data-source spreadsheets
engine/                   The scoring engine (see engine/README.md)
  model.yaml              The model: 25 sub-criteria + editable weights
  score.py                CLI — score & rank candidates
  make_tuning_sheet.py    Generate the Excel weight-tuning workbook
  sync_weights.py         Write edited weights back into model.yaml
  roles/                  Per-requisition role configs
  candidates/             Candidate files to score (sample data included)
  tuning/                 Editable weight-tuning workbook
```

## Quick start

```bash
cd engine
python -m pip install -r requirements.txt
python score.py --role roles/role_mechanical_engineer.yaml --candidates-dir candidates/
```

See **[PROJECT_SCOPE.md](PROJECT_SCOPE.md)** for the vision and roadmap, and
**[engine/README.md](engine/README.md)** for how the engine works and how to tune it.

## Roadmap (summary)

| Phase | Capability |
|---|---|
| 0 ✅ | Find & Rank — scoring engine on resumes/JDs (this repo) |
| 1 | LinkedIn recruiter-in-the-loop capture + Zoho Recruit integration |
| 2 | Reach — personalized outreach |
| 3 | Attract — two-way fit & value proposition |
| 4 | Scale — compliant data provider, multi-user app, agents |
