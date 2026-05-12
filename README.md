# Shopee CX Intelligence Tool
### AI-Augmented Consumer Listening Pipeline

A research tool that transforms raw Google Play reviews into a structured consumer listening report — extracting user pain points, classifying them by feature area and severity, and generating prioritized findings with root cause analysis.

Built as a portfolio project for a CX Researcher role at Shopee Indonesia.

---

## What It Does

```
Google Play Reviews  →  Claude API (Classify)  →  Statistical Analysis  →  Consumer Listening Report
     ~600 reviews           Batch: 20/call         Priority Score (RICE)        Excel + Markdown
```

**Output:** A professional Excel workbook with:
- Executive Summary (decision-ready, 1 page)
- Priority Matrix (ranked by Volume × Severity)
- 3× Deep Dive Research Briefs (root cause + recommendation per top issue)
- Raw classified data (all 600+ reviews tagged)
- Methodology & transparency note

---

## Agentic Flow

This is not a one-shot API call. It's a multi-step research pipeline with quality gates:

| Step | What Happens | Tool |
|------|-------------|------|
| 1. Scrape | Pull 600 reviews, stratified by rating | `google-play-scraper` |
| 2. Classify | Batch classify: feature_area, issue_type, severity 1-5, sentiment | Claude API (Haiku) |
| 3. Quality Gate | Validate 50 random samples, flag if error rate >15% | Python |
| 4. Analyze | Volume ranking, severity weighting, RICE priority score | Pandas |
| 5. Synthesize | Deep dive per top 3 issues: sub-issues, quotes, root cause, recommendation | Claude API (Sonnet) |
| 6. Report | Generate Excel consumer listening report | openpyxl |
| 7. Findings | Write findings markdown as base for PDF report | Python |

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Darmawan19/shopee-cx-intelligence
cd shopee-cx-intelligence
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: add ANTHROPIC_API_KEY

# 3. Run
python pipeline.py

# 4. Find outputs
ls outputs/
# shopee_cx_report_YYYYMMDD_HHMM.xlsx  ← main deliverable
# findings_YYYYMMDD_HHMM.md            ← base for PDF report
```

---

## Research Methodology

**Priority Score** (transparent and defensible):
```
Priority Score = Volume × Avg_Severity × (1 + Widespread_Bonus)
```
Maps to RICE (Reach × Impact × Confidence). Effort excluded — researcher's role is to identify and rank issues, not estimate engineering cost.

**Quality Standards:**
- Quality gate: <15% classification error on validation sample
- Minimum 300 reviews before reporting
- All user quotes preserved in original Bahasa Indonesia
- Limitations section mandatory in every report

---

## Project Structure

```
shopee-cx-intelligence/
├── pipeline.py              # Main orchestrator — run this
├── requirements.txt
├── .env.example
├── SKILL.md                 # Research workflow documentation
├── src/
│   ├── scraper.py           # Step 1: Google Play review collection
│   ├── classifier.py        # Steps 2-3: Claude API batch classification + quality gate
│   ├── analyzer.py          # Step 4: Statistical analysis & RICE prioritization
│   ├── synthesizer.py       # Step 5: Claude API deep dive synthesis
│   └── report_generator.py  # Step 6: Excel report generation
├── prompts/
│   ├── classify_batch.txt   # Batch classification prompt (Indonesian slang-aware)
│   ├── deep_dive.txt        # Per-issue deep dive synthesis prompt
│   └── synthesize_executive.txt  # Executive summary prompt
├── data/                    # Generated during run (gitignored)
└── outputs/                 # Final deliverables (gitignored)
```

---

## Stack

- **Python** — pipeline orchestration
- **google-play-scraper** — public review data collection
- **Anthropic Claude API** — AI-augmented classification and synthesis
- **Pandas** — statistical aggregation
- **openpyxl** — professional Excel report generation

---

## Adapting to Other Apps

Change `APP_ID` in `.env`:
```
APP_ID=com.tokopedia.tkpd  # Tokopedia
APP_ID=com.lazada.android   # Lazada
```
Update `feature_area` taxonomy in `prompts/classify_batch.txt` to match the app's product structure.

---

*Built by Lidharmawan Suryaatmadja | github.com/Darmawan19*
