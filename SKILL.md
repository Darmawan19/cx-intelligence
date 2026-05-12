# cx-research.skill.md
# CX Intelligence Research Workflow

## What This Skill Does

Transforms raw Google Play reviews into a structured consumer listening report with:
- Quantitative issue ranking (volume × severity)
- AI-augmented classification at scale (Claude API)
- Root cause hypotheses per issue area
- RICE-inspired prioritization matrix
- Automated Excel report output

Answers the PM question: *"What's the root cause, which issue is highest in volume, and which ones should we prioritize?"*

---

## When to Trigger This Skill

Use this workflow whenever you need to:
- Extract and analyze user feedback from public review data at scale
- Produce a consumer listening report for stakeholders
- Prioritize UX issues by volume, severity, and user impact
- Understand competitive positioning via public review comparison

---

## Workflow Overview

```
[Data Source]     →    [Classify]    →    [Analyze]    →    [Synthesize]    →    [Report]
Google Play           Claude API         Statistical         Claude API           Excel
Reviews               Batch (20/call)    Aggregation         Deep Dive            PDF
~600-800              feature_area       + RICE Score        per top 3            Findings MD
reviews               issue_type         Priority Rank       issue area
                      severity 1-5
                      sentiment
```

---

## Step-by-Step Agentic Flow

### Step 1 — Data Collection (Deterministic)
```bash
python pipeline.py --step scrape
```
- Tool: `google-play-scraper`
- Target: Shopee Indonesia (`com.shopee.id`), last 6 months
- Sampling: 30% low ratings (1★), weighted for pain point density
- Output: `data/raw_reviews.csv`

### Step 2 — AI Classification (Claude API, batch)
```bash
python pipeline.py --step classify
```
- Batches: 20 reviews per API call
- Model: Claude Haiku (cost-optimized for volume)
- Each review tagged: `feature_area`, `issue_type`, `severity`, `sentiment`, `key_phrase`
- Output: `data/classified_reviews.csv`

### Step 3 — Quality Gate (Automated Validation)
- Samples 50 random reviews
- Validates: rating↔sentiment consistency, rating↔severity correlation
- Threshold: <15% error rate to proceed
- If failed: flag prompt for revision before continuing

### Step 4 — Statistical Analysis
- Volume ranking by feature_area
- Priority Score: `Volume × Avg_Severity × (1 + Widespread_Bonus)`
- Monthly trend distribution
- RICE matrix generation

### Step 5 — Deep Dive Synthesis (Claude API, Sonnet)
- Top 3 issue areas → Claude Sonnet generates research brief
- Each brief includes: sub-issues, representative quotes, root cause hypothesis, recommended action
- Model: Claude Sonnet (quality prioritized for synthesis)

### Step 6 — Report Generation
- Excel workbook: Executive Summary, Priority Matrix, 3× Deep Dives, Raw Data, Methodology
- Findings markdown: base for PDF consumer listening report

---

## Prompts Used

### `classify_batch.txt`
Purpose: Batch classify 20 reviews per call
Key instructions: Indonesian slang handling, severity rubric 1-5, JSON-only output
Output schema: `feature_area`, `issue_type`, `severity`, `sentiment`, `key_phrase`, `user_impact`

### `deep_dive.txt`
Purpose: Synthesize all reviews in one issue area into a research brief
Output: Sub-issues ranked, representative quotes, root cause hypothesis, 1 recommendation

### `synthesize_executive.txt`
Purpose: Generate executive summary for leadership
Tone: Direct, data-backed, no hedging — VP of Product audience

---

## Classification Taxonomy

### Feature Areas
| Code | Label |
|------|-------|
| `checkout_payment` | Checkout & Payment |
| `search_discovery` | Search & Discovery |
| `delivery_logistics` | Delivery & Logistics |
| `seller_experience` | Seller Experience |
| `customer_service` | Customer Service |
| `promotion_voucher` | Promotion & Voucher |
| `app_performance` | App Performance |
| `return_refund` | Return & Refund |
| `account_security` | Account & Security |
| `live_commerce` | Live Commerce |

### Severity Rubric
| Level | Definition |
|-------|-----------|
| 5 | Transaction failure, money lost, data loss — critical |
| 4 | Major blocker: cannot complete core user journey |
| 3 | Significant friction: extra steps, confusion, delays |
| 2 | Frustrating but workaround exists |
| 1 | Minor annoyance, barely affects experience |

---

## Priority Score Formula

```
Priority Score = Volume × Avg_Severity × (1 + Widespread_Bonus)

Where:
  Volume          = number of reviews in this area
  Avg_Severity    = mean severity score (1-5)
  Widespread_Bonus = (% reviews flagged as "likely_widespread") × 0.5
                    → max +50% bonus for systemic issues
```

Rationale: Maps to RICE framework (Reach × Impact × Confidence). Effort excluded — researcher identifies issues, product team estimates fix cost.

---

## Quality Standards

- Minimum reviews: 300 before reporting (statistical reliability)
- Quality gate: <15% classification error on validation sample
- Mandatory limitations section in every report (data source, AI accuracy, selection bias)
- All quotes in original language (Bahasa Indonesia) — no translation that loses nuance

---

## Running the Full Pipeline

```bash
# 1. Setup
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env

# 2. Install
pip install -r requirements.txt

# 3. Full run (all steps)
python pipeline.py

# 4. Step-by-step (for debugging or resuming)
python pipeline.py --step scrape
python pipeline.py --step classify --skip-scrape
python pipeline.py --step analyze --skip-classify
python pipeline.py --step report --skip-classify

# 5. Skip quality gate (proceed despite warnings)
python pipeline.py --skip-quality-gate
```

---

## Output Files

| File | Purpose |
|------|---------|
| `data/raw_reviews.csv` | Raw scraped reviews |
| `data/classified_reviews.csv` | Reviews with AI classification |
| `data/classified_reviews_quality_report.json` | Quality gate results |
| `outputs/shopee_cx_report_YYYYMMDD.xlsx` | Full Excel consumer listening report |
| `outputs/findings_YYYYMMDD.md` | Findings markdown (base for PDF report) |

---

## Adapting This Skill to Other Apps

Change `APP_ID` in `.env` to analyze any Google Play app:
- Tokopedia: `com.tokopedia.tkpd`
- Lazada: `com.lazada.android`
- Grab: `com.grabtaxi.passenger`

Update `feature_area` taxonomy in `prompts/classify_batch.txt` to match the app's product areas.
