# Working on SOURCING

Practical guide for running, tuning, and maintaining the engine. For the vision
and roadmap see [PROJECT_SCOPE.md](PROJECT_SCOPE.md); for how scoring works see
[engine/README.md](engine/README.md).

## Setup (once)

```bash
cd engine
python -m pip install -r requirements.txt
```

Runs fully offline. No API keys or LinkedIn access needed for Phase 0.

## Conventions

- **`engine/model.yaml` is the single source of truth** for the scoring model:
  the 5 categories, their 25 sub-criteria, weights, lexicons, and thresholds.
  Edit weights here (or via the tuning sheet below) — never hard-code them.
- **One role file per requisition** in `engine/roles/` (must-have / nice-to-have
  skills, target employers, standards, languages, region). Phase 1 will
  auto-populate these from Zoho Recruit.
- **`scorer: null`** on a sub-criterion means "not scorable yet" — it scores
  neutral until the data source named in `needs:` is connected. Keep these in the
  model so the weighting reflects the full intended picture.
- **Generated output is not committed** (`engine/reports/` is git-ignored).

## Score & rank candidates

```bash
cd engine
# one candidate -> Markdown scorecard
python score.py --role roles/role_mechanical_engineer.yaml --candidate candidates/marie_tremblay.txt
# a folder -> Excel shortlist + a scorecard each
python score.py --role roles/role_mechanical_engineer.yaml --candidates-dir candidates/
```

## Retune the weights (round-trip)

```bash
cd engine
python make_tuning_sheet.py        # (re)generate tuning/Scoring_Model_Tuning.xlsx from model.yaml
# -> edit the YELLOW cells in Excel; each block must sum to 1.00
python sync_weights.py tuning/Scoring_Model_Tuning.xlsx   # validate + write back into model.yaml
python score.py --role roles/role_mechanical_engineer.yaml --candidates-dir candidates/   # see the effect
```

`sync_weights.py` refuses to write if any block ≠ 1.00 (use `--force` to
normalize). It preserves all comments in `model.yaml`.

## Add a new role

Copy `engine/roles/role_mechanical_engineer.yaml`, give it a new `id`, and fill
in the skills / employers / standards / region. Optionally override
`category_weights` for that role.

## Git workflow

```bash
git add -A
git commit -m "describe the change"
git push
```

Branch off `main` for anything experimental. Credentials are cached by Git
Credential Manager after the first push.
