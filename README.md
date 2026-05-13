# Structured Data Extraction Pipeline

A modular Python pipeline that converts unstructured PDF incident timelines into a structured, schema-validated CSV dataset of **118 fields per record**, with automated standardization, field-level auditing against the source text, and a sanity-check stage that benchmarks extracted row counts against the source document.

Built as part of a research-assistant role at a German university chair, in support of a long-running social-science dataset on conflict-event reporting. Current state: **~500 records extracted, ongoing scaling toward 1,500.**

> ⚠️ Domain note: the dataset documents publicly reported incidents from open-source conflict timelines for academic research purposes. This repository contains only the **extraction engine** — no source PDFs and no extracted research data are included.

---

## What this project demonstrates

- **Real ETL on messy real-world data** — multi-page PDFs with inconsistent formatting, multilingual artifacts, and merged entries
- **Schema-driven engineering** — a single source of truth (`schema.py`) drives extraction, validation, and reporting
- **Multi-stage validation** — extraction → sanity check → standardization → field-level audit, each stage independently testable
- **Position-based NLP without ML** — multi-signal rule pipelines for entity extraction (locations, perpetrators, casualties, victim profiles) achieving **99% cell-level accuracy** on benchmark data
- **Reproducible accuracy reporting** — every pipeline run emits a row-by-row audit report

---

## Architecture

```
┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────┐    ┌──────────┐
│   PDF    │ -> │ extractor  │ -> │ standardize │ -> │  audit   │ -> │  Final   │
│  source  │    │            │    │             │    │          │    │   CSV    │
└──────────┘    └────────────┘    └─────────────┘    └──────────┘    └──────────┘
                      │                  │                 │
                      v                  v                 v
                 sanity check       schema rules      audit report
                (header count)     (118 columns)     (flagged rows)
```

| File              | Lines | Responsibility |
|-------------------|------:|----------------|
| `schema.py`       |   330 | Single source of truth: column order, defaults, allowed values, district mappings |
| `extractor.py`    | 2,150 | PDF parser + per-field extractors (incident type, casualties, locations, perpetrators…) |
| `standardize.py`  |   230 | Enforces schema: column order, null normalization, type coercion |
| `audit.py`        |   430 | Field-level audit against `original_description` — flags inconsistencies |
| `verify.py`       |   585 | Post-pipeline cross-check with confidence-ranked HTML report |
| `pipeline.py`     |   210 | Orchestrator with two modes (PDF → CSV, or CSV → audited CSV) |
| `codebook.py`     | 1,520 | Auto-generated column documentation |

**Total:** ~5,500 lines of Python.

---

## Engineering highlights

### Multi-signal location extraction
Distinguishing *event location* from *victim origin* is non-trivial — sentences like *"a resident of X District was killed in Y District"* require parsing. The pipeline uses position-based signal weighting plus an 80-entry sub-area → district mapping table to resolve these correctly.

### Schema as code
All field defaults, allowed values, type rules, and cross-field constraints live in `schema.py`. Both the standardization stage and the audit stage consume this schema, so a rule change in one place propagates everywhere — no drift.

### Header-count sanity check
Before trusting any extraction run, the pipeline counts `Month - N` header occurrences in the raw PDF text and compares against the per-day row count of the extracted CSV. Mismatches are flagged before any downstream analysis runs.

### Field-level audit, not just type validation
The audit stage re-reads each row's source text and runs ~30 cross-field rules — e.g. "if the text says *eleven coal-mine workers were killed*, `civilian_killed` must equal 11" — flagging rows where the extracted field disagrees with the text. Output: a sorted, confidence-ranked report so the human reviewer sees the most likely errors first.

### Accuracy benchmarks
On the January and February 2025 benchmark documents:
- Row count: **100% match** (75 / 75, 109 / 109)
- February cell-level accuracy: **99.0%** (157 / 17,462 cell diffs)
- District field: 0 errors Jan, 3 edge-case errors Feb

---

## Usage

### Full pipeline (PDF → audited CSV)
```bash
python3 pipeline.py --pdf input.pdf --out output_prefix --month March --year 2025
```

Produces:
- `output_prefix_Full.csv` — raw extraction
- `output_prefix_Full_pipeline.csv` — standardized + audited
- `output_prefix_Full_audit_report.txt` — flagged rows

### Standardize / audit an existing CSV
```bash
python3 pipeline.py existing.csv output.csv
```

### Codebook export
```bash
python3 codebook.py            # writes codebook.md
python3 codebook.py --csv      # writes codebook_reference.csv
```

---

## Requirements

```
pdfplumber
```

Tested on Python 3.11+ and Ubuntu 24.04.

```bash
pip install -r requirements.txt
```

---

## Methodology

Field extraction rules were developed iteratively, using generative AI as a hypothesis generator: candidate regex patterns and edge-case categorizations were proposed, then validated against held-out benchmark CSVs, then either accepted, refined, or rejected based on accuracy impact. This methodological approach connects to coursework on *Generative AI in the Social Sciences* (M.A. Sociology, Data Analytics track, University of Mannheim — grade 1.3).

---

## What's not in this repo

- **Source PDFs** — these come from a third-party publisher and are not redistributed
- **Extracted research data** — the actual `BAL_*.csv` outputs are research artifacts owned by the supervising chair
- **API keys / credentials** — none are required; the pipeline is entirely offline

---

## License

MIT — see [LICENSE](LICENSE).

---

## Contact

Maanvendra Singh — M.A. Sociology (Data Analytics specialization), University of Mannheim
[LinkedIn](https://linkedin.com/in/maanvendra-singh)
