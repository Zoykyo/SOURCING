"""
scoring.py — apply the canonical multi-criteria model (5 categories × 5 sub-criteria)
to a parsed candidate against a role.

The engine is DATA-DRIVEN: it walks `model.yaml`'s categories/sub-criteria and
their weights. Each sub-criterion names a `scorer` (implemented here) or `null`
(scored neutral until its data source is connected). Every score carries evidence
and provenance ('explicit' vs 'no_data') so recruiters can see *why*.
"""

from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass

from parse_profile import CandidateProfile
import reference as ref_lib

_STOPWORDS = {"and", "of", "the", "a", "to", "for", "in", "senior", "junior",
              "lead", "principal", "intermediate"}


# ── text helpers ──────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase + strip accents so Montréal == Montreal."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _contains(text_norm: str, term: str) -> bool:
    return _norm(term) in text_norm


def _matched(text_norm: str, terms: list[str]) -> list[str]:
    return [t for t in terms if _contains(text_norm, t)]


def _lex_hits(raw_text: str, patterns: list[str]) -> list[str]:
    out = []
    for pat in patterns or []:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            out.append(m.group(0))
    return out


def _crit(score, evidence, provenance="explicit"):
    return {"score": float(score), "evidence": evidence, "provenance": provenance}


_CURRENT_RE = re.compile(r"present|current|aujourd|ongoing|to date|–\s*present|-\s*present", re.IGNORECASE)


def current_employer_clients(raw_text: str, client_names: list[str]) -> list[str]:
    """No-poach detection: active-client names appearing on a line marked current
    (contains 'present'/'current'/etc). Past employers are NOT flagged (they're a
    relevance boost, not an exclusion). Heuristic — recruiter confirms."""
    lines = raw_text.splitlines()
    tn_lines = [(ln, _norm(ln)) for ln in lines]
    flagged = []
    for name in client_names:
        n = _norm(name)
        for ln, lnn in tn_lines:
            if n in lnn and _CURRENT_RE.search(ln):
                flagged.append(name)
                break
    return flagged


# ── scoring context shared by all sub-scorers ─────────────────────────────────

@dataclass
class Ctx:
    cand: CandidateProfile
    role: dict
    model: dict
    tn: str                 # normalized full text
    lex: dict               # lexicons
    must: list
    nice: list
    stds: list
    must_hit: list
    nice_hit: list
    std_hit: list
    target_employers: list  # role's explicit list UNION sector auto-fill


# ── sub-criterion scorers (keyed by the `scorer:` name in model.yaml) ─────────

def employers_relevance(c: Ctx):
    targets = c.target_employers
    if not targets:
        return _crit(50, "No target employers defined for role", "no_data")
    hit = _matched(c.tn, targets)
    if hit:
        shown = ", ".join(hit[:6]) + ("…" if len(hit) > 6 else "")
        return _crit(100, f"Worked at sector-relevant company/OEM: {shown}")
    return _crit(40, "No sector-relevant company found in profile")


def role_relevance(c: Ctx):
    tokens = [t for t in re.findall(r"[a-z&]+", _norm(c.role.get("title", "")))
              if t not in _STOPWORDS and len(t) > 2]
    if not tokens:
        return _crit(50, "No role title to match", "no_data")
    hit = [t for t in tokens if t in c.tn]
    return _crit(100 * len(hit) / len(tokens),
                 f"Title keywords matched: {', '.join(hit) or 'none'} ({len(hit)}/{len(tokens)})")


def seniority_match(c: Ctx):
    yrs, target, bands = c.cand.years_experience, c.role.get("seniority"), c.model["seniority_bands"]
    if yrs is None or target not in bands:
        return _crit(50, "Years of experience not stated", "no_data")
    b = bands[target]
    if b["min"] <= yrs <= b["max"]:
        return _crit(100, f"{yrs:g} yrs fits '{target}' band ({b['min']}–{b['max']})")
    dist = (b["min"] - yrs) if yrs < b["min"] else (yrs - b["max"])
    return _crit(max(40, 100 - dist * 15),
                 f"{yrs:g} yrs vs '{target}' band ({b['min']}–{b['max']}) — off by {dist:g}")


def key_competencies(c: Ctx):
    """Blend must-have (70%) and nice-to-have (30%) coverage. (Gate handled separately.)"""
    if not c.must and not c.nice:
        return _crit(50, "No skills defined for role", "no_data")
    must_frac = (len(c.must_hit) / len(c.must)) if c.must else None
    nice_frac = (len(c.nice_hit) / len(c.nice)) if c.nice else None
    if must_frac is not None and nice_frac is not None:
        score = 100 * (0.7 * must_frac + 0.3 * nice_frac)
    elif must_frac is not None:
        score = 100 * must_frac
    else:
        score = 100 * nice_frac
    ev = (f"Must-have {len(c.must_hit)}/{len(c.must)} [{', '.join(c.must_hit) or 'none'}]; "
          f"Nice-to-have {len(c.nice_hit)}/{len(c.nice)} [{', '.join(c.nice_hit) or 'none'}]")
    return _crit(score, ev)


def standards_match(c: Ctx):
    if not c.stds:
        return _crit(50, "No standards defined", "no_data")
    return _crit(100 * len(c.std_hit) / len(c.stds),
                 f"Standards {len(c.std_hit)}/{len(c.stds)}: {', '.join(c.std_hit) or 'none'}")


def education(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("education", []))
    if not hits:
        return _crit(50, "No education signals detected", "no_data")
    low = _norm(" ".join(hits))
    if any(k in low for k in ("phd", "ph.d", "doctorate")):
        return _crit(100, f"Doctoral-level education: {', '.join(hits)}")
    if any(k in low for k in ("master", "m.eng", "meng", "m.sc", "msc", "mba")):
        return _crit(90, f"Master's-level education: {', '.join(hits)}")
    return _crit(75, f"Education signals: {', '.join(hits)}")


def languages_match(c: Ctx):
    req = c.role.get("languages", [])
    if not req:
        return _crit(50, "No languages required", "no_data")
    if not c.cand.languages:
        return _crit(50, "Candidate languages not stated", "no_data")
    cand_norm = _norm(" ".join(c.cand.languages))
    hit = [l["name"] for l in req if _norm(l["name"]) in cand_norm]
    return _crit(100 * len(hit) / len(req),
                 f"Languages {len(hit)}/{len(req)}: {', '.join(hit) or 'none'}")


def certifications(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("certifications", []))
    if not hits:
        return _crit(50, "No certifications/credentials detected", "no_data")
    return _crit(min(100, 55 + 15 * len(hits)),
                 f"{len(hits)} credential signal(s): {', '.join(hits)}")


def awards(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("awards", []))
    if not hits:
        return _crit(50, "No awards/honors detected", "no_data")
    return _crit(min(100, 40 + 20 * len(hits)), f"{len(hits)} award/honor signal(s): {', '.join(hits)}")


def authority(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("authority", []))
    if not hits:
        return _crit(50, "No domain-authority signals detected", "no_data")
    return _crit(min(100, 40 + 20 * len(hits)), f"{len(hits)} authority signal(s): {', '.join(hits)}")


def publications(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("publications", []))
    if not hits:
        return _crit(50, "No publications/patents detected", "no_data")
    return _crit(min(100, 40 + 25 * len(hits)), f"{len(hits)} publication/patent signal(s): {', '.join(hits)}")


def competition(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("competition", []))
    if not hits:
        return _crit(50, "No competition/student-club signals", "no_data")
    return _crit(min(100, 60 + 15 * len(hits)), f"Competition signal(s): {', '.join(hits)}")


def recognition(c: Ctx):
    """Merged distinction signal: awards/honors + demonstrated authority + competitions."""
    hits = (_lex_hits(c.cand.raw_text, c.lex.get("awards", [])) +
            _lex_hits(c.cand.raw_text, c.lex.get("authority", [])) +
            _lex_hits(c.cand.raw_text, c.lex.get("competition", [])))
    if not hits:
        return _crit(50, "No recognition signals (awards/authority/competition)", "no_data")
    return _crit(min(100, 40 + 18 * len(hits)), f"{len(hits)} recognition signal(s): {', '.join(hits)}")


def open_to_work(c: Ctx):
    if c.cand.open_to_work_signals:
        return _crit(100, f"Openness signal(s): {', '.join(c.cand.open_to_work_signals)}")
    return _crit(50, "No explicit openness signal (unknown)", "no_data")


def tenure_windows(c: Ctx):
    if c.cand.open_to_work_signals:
        return _crit(80, "Openness implies readiness to move")
    return _crit(50, "Tenure/readiness not determinable from text", "no_data")


def location_proximity(c: Ctx):
    region = c.role.get("region")
    if not region or not c.cand.location:
        return _crit(50, "Location or region not stated", "no_data")
    rt = set(re.findall(r"[a-z]+", _norm(region)))
    lt = set(re.findall(r"[a-z]+", _norm(c.cand.location)))
    overlap = rt & lt
    if overlap:
        return _crit(100, f"Location overlaps role region on: {', '.join(sorted(overlap))}")
    if c.cand.relocation_signals:
        return _crit(80, "Different region but signals willingness to relocate")
    return _crit(40, f"Location '{c.cand.location}' differs from role region '{region}'")


def work_mode_fit(c: Ctx):
    if c.cand.relocation_signals:
        return _crit(70, "Mobility signals suggest flexibility on work mode")
    return _crit(50, f"Work-mode preference unknown (role wants {c.role.get('work_mode','?')})", "no_data")


def interest_relocation(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("interest_relocation", []))
    if hits:
        return _crit(100, f"Relocation interest: {', '.join(hits)}")
    return _crit(50, "No relocation-interest signal (unknown)", "no_data")


def willingness_travel(c: Ctx):
    hits = _lex_hits(c.cand.raw_text, c.lex.get("willingness_travel", []))
    if hits:
        return _crit(100, f"Travel willingness: {', '.join(hits)}")
    return _crit(50, "No travel-willingness signal (unknown)", "no_data")


SCORERS = {
    "employers_relevance": employers_relevance,
    "role_relevance": role_relevance,
    "seniority_match": seniority_match,
    "key_competencies": key_competencies,
    "standards_match": standards_match,
    "education": education,
    "languages_match": languages_match,
    "certifications": certifications,
    "awards": awards,
    "authority": authority,
    "publications": publications,
    "competition": competition,
    "recognition": recognition,
    "open_to_work": open_to_work,
    "tenure_windows": tenure_windows,
    "location_proximity": location_proximity,
    "work_mode_fit": work_mode_fit,
    "interest_relocation": interest_relocation,
    "willingness_travel": willingness_travel,
}


# ── orchestration ─────────────────────────────────────────────────────────────

def score_candidate(cand: CandidateProfile, role: dict, model: dict, reference: dict | None = None) -> dict:
    tn = _norm(cand.raw_text)
    lex = model.get("lexicons", {})
    must = role.get("must_have_skills", [])
    nice = role.get("nice_to_have_skills", [])
    stds = role.get("standards", [])

    # Relevance boost: role's explicit target employers UNION the sector's companies.
    sector = role.get("sector")
    sector_fill = ref_lib.companies_for_sector(reference, sector)
    target_employers = list(dict.fromkeys(list(role.get("target_employers", [])) + sector_fill))

    ctx = Ctx(cand=cand, role=role, model=model, tn=tn, lex=lex,
              must=must, nice=nice, stds=stds,
              must_hit=_matched(tn, must), nice_hit=_matched(tn, nice), std_hit=_matched(tn, stds),
              target_employers=target_employers)

    cat_overrides = role.get("category_weights") or {}
    no_data = model["no_data_score"]
    gate_pass = model["thresholds"].get("gate_pass_score", 60)

    def run_sub(sub):
        scorer = sub.get("scorer")
        if scorer and scorer in SCORERS:
            res = SCORERS[scorer](ctx)
        else:
            res = _crit(no_data, f"Not yet scored — needs {sub.get('needs', 'richer data')}", "no_data")
        res["label"] = sub["label"]
        res["weight"] = sub.get("weight", 0)
        res["fairness_flag"] = sub.get("fairness_flag")
        return res

    categories_out = {}
    cat_scores = {}
    feasibility = []          # gate checks (pass / review / unknown) — not scored
    for cat_id, cat in model["categories"].items():
        subs_out = {}
        for sub in cat["subcriteria"]:
            res = run_sub(sub)
            if sub.get("gate"):
                status = ("unknown" if res["provenance"] == "no_data"
                          else "pass" if res["score"] >= gate_pass else "review")
                feasibility.append({"id": sub["id"], "label": sub["label"],
                                    "status": status, "evidence": res["evidence"]})
                continue
            subs_out[sub["id"]] = res

        num = sum(r["score"] * r["weight"] for r in subs_out.values())
        den = sum(r["weight"] for r in subs_out.values())
        score = num / den if den else 0.0
        cat_scores[cat_id] = round(score, 1)
        categories_out[cat_id] = {
            "label": cat["label"],
            "weight": cat_overrides.get(cat_id, cat["weight"]),
            "score": round(score, 1),
            "subcriteria": subs_out,
        }

    total = sum(categories_out[c]["score"] * categories_out[c]["weight"] for c in categories_out)

    # Must-have gate (independent of weighting).
    must_frac = (len(ctx.must_hit) / len(must)) if must else 1.0
    gate_passed = must_frac >= model["thresholds"]["must_have_gate"]
    missing_must = [m for m in must if m not in ctx.must_hit]

    wow = _wow(model, total, gate_passed, ctx)

    # No-poach: currently employed at an active client (firm-wide) OR at the
    # hiring client we're sourcing FOR this search.
    protected = list(ref_lib.active_client_names(reference))
    hiring_client = role.get("hiring_client") or role.get("client")
    if hiring_client:
        protected.append(hiring_client)
    no_poach_hits = current_employer_clients(cand.raw_text, protected)
    no_poach = {"triggered": bool(no_poach_hits), "companies": no_poach_hits}

    all_subs = [r for cat in categories_out.values() for r in cat["subcriteria"].values()]
    explicit = sum(1 for r in all_subs if r["provenance"] == "explicit")
    completeness = explicit / len(all_subs)

    status = ("⛔ No-poach — currently at active client" if no_poach["triggered"]
              else "Below bar — missing must-haves" if not gate_passed
              else "Shortlist" if total >= model["thresholds"]["shortlist_min_score"]
              else "Marginal")

    return {
        "candidate": cand.name,
        "role": role.get("id"),
        "total_score": round(total, 1),
        "category_scores": cat_scores,
        "categories": categories_out,
        "feasibility": feasibility,
        "gate_passed": gate_passed,
        "missing_must_haves": missing_must,
        "no_poach": no_poach,
        "wow": wow,
        "status": status,
        "data_completeness": round(completeness, 2),
        "provenance": cand.provenance,
    }


def _wow(model, total, gate_passed, ctx: Ctx) -> bool:
    r = model["wow_rule"]
    if r.get("require_all_must_haves") and not gate_passed:
        return False
    if r.get("require_min_score") and total < model["thresholds"]["wow_min_score"]:
        return False
    if r.get("require_distinction"):
        has_distinction = any(_lex_hits(ctx.cand.raw_text, ctx.lex.get(k, []))
                              for k in ("awards", "authority", "publications"))
        if not has_distinction:
            return False
    if r.get("require_employer_or_standards"):
        emp = bool(_matched(ctx.tn, ctx.target_employers))
        if not (emp or ctx.std_hit):
            return False
    return True
