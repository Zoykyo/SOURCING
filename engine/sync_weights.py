"""
sync_weights.py — read an edited tuning workbook and write its weights back into
model.yaml (comments preserved via targeted line edits).

    python sync_weights.py                                  # default tuning file
    python sync_weights.py path/to/edited.xlsx              # explicit file
    python sync_weights.py edited.xlsx --force              # write even if a block != 1.00

Validates that category weights sum to 1.00 and each category's sub-weights sum to
1.00 before writing. Use --force to normalize-and-write anyway.
"""

from __future__ import annotations
import sys
from pathlib import Path
import re
import yaml
import openpyxl

HERE = Path(__file__).parent
MODEL = HERE / "model.yaml"
DEFAULT_SHEET = HERE / "tuning" / "Scoring_Model_Tuning.xlsx"
TOL = 0.005


def read_sheet_weights(xlsx: Path):
    """Return (cat_weights{cat_label:w}, sub_weights{sub_label:w}) read from the sheet."""
    model = yaml.safe_load(MODEL.read_text(encoding="utf-8"))
    cat_labels = {c["label"]: cid for cid, c in model["categories"].items()}
    sub_labels = {}
    for cid, c in model["categories"].items():
        for s in c["subcriteria"]:
            sub_labels[s["label"]] = s["id"]

    ws = openpyxl.load_workbook(xlsx, data_only=True).active
    cat_w, sub_w = {}, {}
    for row in ws.iter_rows():
        a = row[0].value if len(row) > 0 else None
        b = row[1].value if len(row) > 1 else None
        c = row[2].value if len(row) > 2 else None
        if a in cat_labels and isinstance(b, (int, float)):
            cat_w[cat_labels[a]] = float(b)
        if b in sub_labels and isinstance(c, (int, float)):
            sub_w[sub_labels[b]] = float(c)
    return model, cat_w, sub_w


def validate(model, cat_w, sub_w):
    errs = []
    missing_cat = [cid for cid in model["categories"] if cid not in cat_w]
    if missing_cat:
        errs.append(f"Missing category weights for: {missing_cat}")
    tot = sum(cat_w.values())
    if abs(tot - 1) > TOL:
        errs.append(f"Category weights sum to {tot:.3f} (must be 1.00)")
    for cid, c in model["categories"].items():
        ids = [s["id"] for s in c["subcriteria"]]
        missing = [i for i in ids if i not in sub_w]
        if missing:
            errs.append(f"[{cid}] missing sub-weights: {missing}")
            continue
        s = sum(sub_w[i] for i in ids)
        if abs(s - 1) > TOL:
            errs.append(f"[{cid}] sub-weights sum to {s:.3f} (must be 1.00)")
    return errs


def normalize(model, cat_w, sub_w):
    tot = sum(cat_w.values()) or 1
    cat_w = {k: v / tot for k, v in cat_w.items()}
    for cid, c in model["categories"].items():
        ids = [s["id"] for s in c["subcriteria"]]
        s = sum(sub_w.get(i, 0) for i in ids) or 1
        for i in ids:
            sub_w[i] = sub_w.get(i, 0) / s
    return cat_w, sub_w


def write_model(model, cat_w, sub_w):
    """Targeted in-place edit of weight: lines, preserving comments/formatting."""
    # id -> sub weight; track category context by indentation.
    lines = MODEL.read_text(encoding="utf-8").splitlines()
    out = []
    in_categories = False
    cur_cat = None
    cur_sub = None
    changed = 0
    for ln in lines:
        m_top = re.match(r"^(\w+):", ln)
        if m_top:
            in_categories = (m_top.group(1) == "categories")
        if in_categories:
            m_cat = re.match(r"^  (\w+):\s*$", ln)
            m_sub = re.match(r"^      - id:\s*(\w+)", ln)
            if m_cat:
                cur_cat, cur_sub = m_cat.group(1), None
            elif m_sub:
                cur_sub = m_sub.group(1)
            m_catw = re.match(r"^(    weight:\s*)([\d.]+)(.*)$", ln)
            m_subw = re.match(r"^(        weight:\s*)([\d.]+)(.*)$", ln)
            if m_subw and cur_sub in sub_w:
                ln = f"{m_subw.group(1)}{round(sub_w[cur_sub], 4)}{m_subw.group(3)}"
                changed += 1
            elif m_catw and cur_cat in cat_w:
                ln = f"{m_catw.group(1)}{round(cat_w[cur_cat], 4)}{m_catw.group(3)}"
                changed += 1
        out.append(ln)
    MODEL.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def main(argv=None):
    argv = argv or sys.argv[1:]
    force = "--force" in argv
    paths = [a for a in argv if not a.startswith("--")]
    xlsx = Path(paths[0]) if paths else DEFAULT_SHEET
    if not xlsx.exists():
        print(f"✗ Tuning file not found: {xlsx}")
        return 1

    model, cat_w, sub_w = read_sheet_weights(xlsx)
    errs = validate(model, cat_w, sub_w)
    if errs and not force:
        print("✗ Validation failed — nothing written:")
        for e in errs:
            print("   -", e)
        print("\nFix the sheet (each block must sum to 1.00) or re-run with --force to normalize.")
        return 1
    if errs and force:
        print("⚠️  --force: normalizing weights to sum to 1.00")
        cat_w, sub_w = normalize(model, cat_w, sub_w)

    n = write_model(model, cat_w, sub_w)
    print(f"✓ Wrote {n} weights into {MODEL.name}")
    print("  Category weights:", {k: round(v, 3) for k, v in cat_w.items()})
    print("\nNext: re-run scoring →")
    print("  python score.py --role roles/role_mechanical_engineer.yaml --candidates-dir candidates/")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    raise SystemExit(main())
