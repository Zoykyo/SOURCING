# SOURCING — Project Scope

> Smart sourcing tool to help Kollabtek recruiters **find, reach, and attract** top technical candidates.
> Last updated: 2026-06-08

---

## 1. Vision

Turn Kollabtek's existing **Multi-Criteria Sourcing Model** (already drafted in the Knowledge Base) into a working
tool that helps recruiters surface, score, and engage the best candidates for technical/engineering roles
(aerospace/automotive signals: OEM, SAE, ISO).

The full product spans three capabilities; we build them in order:

```
FIND & RANK  →  REACH  →  ATTRACT
(MVP)           (Phase 2)   (Phase 3)
```

Long-term form factor (confirmed): scoring engine **+** web app **+** AI agents **+** ATS integration.
We start lean (local Python) and grow into that without boxing ourselves in.

---

## 2. Decisions locked in (from scoping)

| Question | Decision |
|---|---|
| First capability (MVP) | **Find & rank** — operationalize the multi-criteria model into a scored shortlist |
| Primary candidate pool | **LinkedIn-centric** |
| LinkedIn access method | **Recruiter-in-the-loop Chrome extension** (human-triggered, low-volume, ToS-aware). NOT bulk scraping. |
| System of record | **Zoho Recruit** (read roles, write back scored candidates/shortlists via Zoho API) |
| Data systems today | ATS/CRM (Zoho) + LinkedIn Recruiter / Sales Navigator |
| Build & host | **Just us, locally** — Python tools on Windows; design clean enough to grow later |
| Eventual scope | Engine → Web app → Agents → ATS-integrated |

---

## 3. MVP — "Find & Rank" (precise scope)

**Goal:** Given a role, produce a ranked, transparently-scored candidate shortlist using the 5-category model.

**Flow:**
1. **Role intake** — pull a requisition from Zoho Recruit (or paste a job description). Parse into a structured
   *Role Profile*: must-have vs. nice-to-have competencies, seniority, region, OEM/standards, work mode, etc.
2. **Candidate capture** — recruiter browses a profile in LinkedIn Recruiter/Sales Nav; the Chrome extension
   captures the on-screen profile and sends it to the local engine. (Also: import resumes already in the folder.)
3. **Parse & enrich** — normalize the profile; use an LLM to infer "the unspoken" (Phase-2 enrichment model)
   and fill partial/missing fields with confidence flags.
4. **Score** — apply the multi-criteria model → category scores + weighted total + the "Bonus/added-value (A+B+C=Wow!)" flag.
5. **Output** — ranked shortlist with a per-candidate scorecard explaining *why* (evidence per criterion).
   Optionally push the shortlist + scores back to Zoho.

**Explicitly OUT of MVP scope:** outreach/messaging (Reach), employer value-prop generation (Attract),
multi-user web app, autonomous agents, any bulk/automated LinkedIn crawling.

---

## 4. Operationalizing the Multi-Criteria Model

The drafted model becomes a configurable scoring schema. Each of the 5 categories → criteria → signals → score.

| # | Category | Drives | Scoring notes |
|---|---|---|---|
| 1 | Professional Profile & Career Trajectory | Fit of history/progression | Must-have gating + relevance weighting |
| 2 | Skills, Expertise & Qualifications | Technical fit | **Must-have vs nice-to-have** split is the gate |
| 3 | Credibility, Reputation & Distinction | Quality signal | Bonus/upside; awards, patents, speaking |
| 4 | Availability & Retention Potential | Reachability + likelihood to move/stay | Open-to-work, tenure windows, interest signals |
| 5 | Mobility | Relocation/travel/work-mode fit | Often a hard filter per role |

**Cross-cutting (Phase-2 ideas, baked in early):**
- **Bonus / added-value model** — detect rare combinations that make a profile "Wow."
- **Enrichment model ("the unspoken")** — LLM-inferred fields with confidence + provenance, never silently treated as fact.

Weights and must-have rules should be **configurable per role** — different roles weight the categories differently.

---

## 5. Proposed architecture (MVP, local)

```
┌─────────────────────┐     ┌──────────────────────────┐     ┌────────────────────┐
│ Chrome extension    │────▶│  Local engine (Python)   │────▶│  Local store        │
│ (recruiter-in-loop) │     │  - role parser           │     │  (SQLite)           │
│ captures on-screen  │     │  - profile parser        │     │  roles / candidates │
│ LinkedIn profile    │     │  - enrichment (LLM)      │     │  scores / evidence  │
└─────────────────────┘     │  - scoring engine        │     └────────────────────┘
                            │  - report generator      │
┌─────────────────────┐     │                          │     ┌────────────────────┐
│ Resume / file import│────▶│                          │────▶│  Zoho Recruit (API) │
│ (existing folder)   │     └──────────────────────────┘     │  read roles /       │
└─────────────────────┘              │                       │  write shortlists   │
                                     ▼                       └────────────────────┘
                            Scorecards (xlsx / md / html)
```

**Components**
- **Chrome extension** (JS) — minimal: capture current profile, POST to local engine, show the score inline. Human-triggered only.
- **Engine** (Python) — role parser, profile parser, enrichment, scoring, reporting. Reuses the openpyxl work already here.
- **LLM** — Claude API for parsing unstructured text, enrichment/"unspoken" inference, and (later) outreach drafting.
- **Store** — SQLite locally (clean upgrade path to Postgres/cloud later).
- **Zoho Recruit API** — roles in, scored candidates out.

---

## 6. Tech stack

- **Language:** Python 3.x (matches existing `build_sourcing_model.py`)
- **Storage:** SQLite → (later) Postgres/cloud
- **LLM:** Anthropic Claude API (`claude-opus-4-8` / `claude-sonnet-4-6` for cheaper bulk parsing)
- **Capture:** Chrome extension (Manifest V3, vanilla JS)
- **Integrations:** Zoho Recruit REST API; resume parsing for existing files
- **Reporting:** openpyxl (xlsx scorecards) + simple HTML/Markdown

---

## 7. Phased roadmap

| Phase | Capability | Highlights |
|---|---|---|
| **0 — Foundation** ✅ BUILT | Scoring schema + scorecard from a resume/JD, no LinkedIn yet | Working engine in `engine/` — runs offline; see `engine/README.md` |
| **1 — MVP Find & Rank** | Chrome capture → enrich → score → shortlist; Zoho read/write | The core sourcing assistant |
| **2 — Reach** | Outreach drafting, contact-channel analysis, sequencing | Personalized messaging from the scorecard |
| **3 — Attract** | Two-way fit + value-prop generation (what Kollabtek/clients can offer) | Motivation matching |
| **4 — Scale & agents** | Compliant data-provider option, multi-user web app, semi-autonomous agents | Grow beyond local/manual |

---

## 8. Key risks & mitigations

- **LinkedIn ToS** — keep capture human-triggered & low-volume; no bulk crawl; plan compliant data-provider as the scaling path.
- **Privacy / candidate PII (Québec Law 25 / GDPR)** — store minimal data, track provenance & consent basis, support deletion. Worth a deliberate data-governance pass.
- **Enrichment hallucination** — every inferred field carries a confidence score + source; recruiters see what's fact vs. inferred.
- **Scoring trust** — scores must be explainable (evidence per criterion) or recruiters won't adopt them.
- **Zoho API specifics** — confirm edition/API access and field schema before building write-back.

---

## 9. Open questions to resolve before/while building

1. **Zoho Recruit**: which edition, and do we have API/admin access + a sandbox?
2. **Weights**: who owns the per-role weighting of the 5 categories? Start with sensible defaults?
3. **Volume**: how many open roles and recruiters at once (sizing the local approach)?
4. **Existing data**: can we use the resumes / 5-yr requisition history / Genium survey already referenced as test data and as an "own database" pre-filter?
5. **Compliance appetite**: confirm comfort with the recruiter-in-the-loop Chrome model vs. moving to a licensed data provider sooner.

---

## 10. Immediate next steps (proposed)

1. **Phase 0 build:** turn the 5-category model into a configurable scoring schema (YAML/JSON) + a script that scores one resume/JD and emits a scorecard. Uses data already in the folder — no LinkedIn needed.
2. Confirm **Zoho Recruit** edition/API access.
3. Prototype the **Chrome capture** on a single profile to validate the recruiter-in-the-loop flow.
