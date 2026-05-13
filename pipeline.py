"""
pipeline.py — Main Orchestrator for Shopee CX Intelligence Tool

Runs the full agentic research flow:
  Step 1: Scrape reviews from Google Play
  Step 2: Classify all reviews via Claude API (batch)
  Step 3: Quality gate — validate classification accuracy
  Step 4: Statistical analysis & prioritization
  Step 5: Deep-dive synthesis via Claude API (Sonnet)
  Step 6: Generate Excel consumer listening report
  Step 7: Generate findings markdown (for PDF report)

Usage:
  python pipeline.py                    # Full run
  python pipeline.py --step scrape      # Only step 1
  python pipeline.py --step classify    # Steps 2-3 (needs raw_reviews.csv)
  python pipeline.py --step analyze     # Step 4 (needs classified_reviews.csv)
  python pipeline.py --step report      # Steps 5-6 (needs analysis done)
  python pipeline.py --skip-scrape      # Skip step 1, use existing raw data
  python pipeline.py --skip-quality-gate  # Skip gate even if failed
"""

import os
import sys
import json
import argparse
import subprocess
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ── Import pipeline stages ─────────────────────────────────────────────────────
from src.scraper import scrape_reviews, save_raw
from src.classifier import classify_all, quality_gate, save_classified
from src.analyzer import analyze, save_analysis
from src.synthesizer import synthesize_deep_dives, synthesize_executive_summary
from src.report_generator import generate_excel_report


# ── Paths ──────────────────────────────────────────────────────────────────────
RAW_PATH = "data/raw_reviews.csv"
CLASSIFIED_PATH = "data/classified_reviews.csv"
QUALITY_PATH = "data/classified_reviews_quality_report.json"
ANALYSIS_PATH = "data/analysis_results.csv"
REPORT_PATH = f"outputs/shopee_cx_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
FINDINGS_PATH = f"outputs/findings_{datetime.now().strftime('%Y%m%d_%H%M')}.md"


def banner():
    print("\n" + "="*60)
    print("  SHOPEE CX INTELLIGENCE TOOL")
    print("  AI-Augmented Consumer Listening Pipeline")
    print("  by Lidharmawan Suryaatmadja")
    print("="*60)


def check_api_key():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set")
        print("   Copy .env.example to .env and add your API key")
        sys.exit(1)


def step1_scrape(args) -> pd.DataFrame:
    """Step 1: Scrape reviews"""
    if args.skip_scrape and Path(RAW_PATH).exists():
        print(f"\n[STEP 1 / SCRAPER] Loading existing data from {RAW_PATH}")
        df = pd.read_csv(RAW_PATH, parse_dates=["date"])
        print(f"  Loaded {len(df)} reviews")
        return df
    
    count = int(os.getenv("SCRAPE_COUNT", 600))
    lang = os.getenv("SCRAPE_LANG", "id")
    country = os.getenv("SCRAPE_COUNTRY", "id")
    
    df = scrape_reviews(total_count=count, lang=lang, country=country)
    save_raw(df, RAW_PATH)
    return df


def step2_classify(df: pd.DataFrame, args) -> tuple[pd.DataFrame, dict]:
    """Steps 2-3: Classify + quality gate"""
    if args.skip_classify and Path(CLASSIFIED_PATH).exists():
        print(f"\n[STEP 2 / CLASSIFIER] Loading existing classified data")
        classified = pd.read_csv(CLASSIFIED_PATH, parse_dates=["date"])
        with open(QUALITY_PATH) as f:
            quality_report = json.load(f)
        print(f"  Loaded {len(classified)} classified reviews")
        return classified, quality_report
    
    classified = classify_all(df)
    quality_report = quality_gate(classified)
    
    if not quality_report["passed"] and not args.skip_quality_gate:
        print(f"\n⚠ Quality gate failed (error rate: {quality_report['error_rate']:.1%})")
        print("  Run with --skip-quality-gate to proceed anyway")
        print("  Or inspect prompts/classify_batch.txt and adjust")
        sys.exit(1)
    
    save_classified(classified, quality_report, CLASSIFIED_PATH)

    other_pct = (classified["feature_area"] == "other").mean() * 100
    if other_pct > 20:
        print(f"\n[CLASSIFIER] 'Other' bucket {other_pct:.1f}% > 20% threshold — running re-classification pass...")
        import reclassify_other
        classified = reclassify_other.run(classified)
        classified = pd.read_csv(CLASSIFIED_PATH, parse_dates=["date"])
        new_pct = (classified["feature_area"] == "other").mean() * 100
        print(f"[CLASSIFIER] Re-classification done — 'other' reduced to {new_pct:.1f}%")

    return classified, quality_report


def step4_analyze(classified: pd.DataFrame) -> dict:
    """Step 4: Statistical analysis"""
    results = analyze(classified)
    save_analysis(results, ANALYSIS_PATH)
    return results


def step5_synthesize(results: dict) -> tuple[dict, str]:
    """Step 5: Deep dive synthesis"""
    deep_dives = synthesize_deep_dives(results)
    exec_summary = synthesize_executive_summary(results, deep_dives)
    return deep_dives, exec_summary


def step6_report(results: dict, deep_dives: dict, exec_summary: str, quality_report: dict) -> str:
    """Step 6: Generate Excel report"""
    return generate_excel_report(results, deep_dives, exec_summary, quality_report, REPORT_PATH)


def step7_findings_md(results: dict, deep_dives: dict, exec_summary: str) -> str:
    """Step 7: Generate Markdown findings (for building the PDF report)"""
    print(f"\n[STEP 7 / FINDINGS] Writing findings markdown...")
    
    summary = results["summary"]
    area_stats = results["area_stats"]
    from src.analyzer import FEATURE_AREA_LABELS

    lines = [
        "# Shopee Indonesia — Consumer Listening Report",
        f"**Date range:** {summary['date_range_start']} to {summary['date_range_end']}",
        f"**Reviews analyzed:** {summary['total_reviews']:,}",
        f"**Generated:** {summary['generated_at']}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        exec_summary,
        "",
        "---",
        "",
        "## Priority Issue Matrix",
        "",
        "| Rank | Issue Area | Volume | Avg Severity | Priority Score |",
        "|------|-----------|--------|-------------|---------------|",
    ]

    for _, row in area_stats[area_stats["feature_area"] != "other"].head(8).iterrows():
        lines.append(
            f"| #{int(row['rank'])} | {row['label']} | {int(row['volume'])} | "
            f"{row['avg_severity']:.2f}/5 | {row['priority_score']:.1f} |"
        )

    lines += ["", "---", "", "## Deep Dive Analysis", ""]

    for i, (area, brief) in enumerate(deep_dives.items(), 1):
        label = FEATURE_AREA_LABELS.get(area, area)
        lines += [f"### Deep Dive {i}: {label}", "", brief, "", "---", ""]

    lines += [
        "## Methodology",
        "",
        f"- **Source:** Google Play Store, Shopee Indonesia (com.shopee.id)",
        f"- **Classification:** AI-augmented via Claude API (batch processing)",
        f"- **Prioritization:** Volume × Avg Severity × (1 + Widespread Bonus)",
        f"- **Sample size:** {summary['total_reviews']:,} reviews, {summary['date_range_start']} to {summary['date_range_end']}",
        f"- **Limitations:** Single-source (Google Play), language: Bahasa Indonesia primary",
    ]

    os.makedirs(os.path.dirname(FINDINGS_PATH), exist_ok=True)
    with open(FINDINGS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[FINDINGS] ✓ Saved → {FINDINGS_PATH}")
    return FINDINGS_PATH


def main():
    parser = argparse.ArgumentParser(description="Shopee CX Intelligence Pipeline")
    parser.add_argument("--step", choices=["scrape", "classify", "analyze", "report", "full"],
                        default="full", help="Which step to run")
    parser.add_argument("--skip-scrape", action="store_true",
                        help="Skip scraping, use existing raw_reviews.csv")
    parser.add_argument("--skip-classify", action="store_true",
                        help="Skip classification, use existing classified_reviews.csv")
    parser.add_argument("--skip-quality-gate", action="store_true",
                        help="Proceed even if quality gate fails")
    args = parser.parse_args()

    banner()
    check_api_key()

    print(f"\n▶ Mode: {args.step.upper()}")
    start_time = datetime.now()

    # ── Run pipeline ────────────────────────────────────────────────────────────

    df_raw = step1_scrape(args)

    if args.step == "scrape":
        print("\n✓ Step 1 complete. Run with --step classify to continue.")
        return

    classified, quality_report = step2_classify(df_raw, args)

    if args.step == "classify":
        print("\n✓ Steps 2-3 complete. Run with --step analyze to continue.")
        return

    results = step4_analyze(classified)

    if args.step == "analyze":
        print("\n✓ Step 4 complete. Run with --step report to continue.")
        return

    deep_dives, exec_summary = step5_synthesize(results)
    report_path = step6_report(results, deep_dives, exec_summary, quality_report)
    findings_path = step7_findings_md(results, deep_dives, exec_summary)

    subprocess.run(["python", "scripts/monthly_summary.py"], check=False)

    # ── Final summary ───────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start_time).seconds
    mins, secs = divmod(elapsed, 60)

    print(f"\n{'='*60}")
    print(f"  ✅ PIPELINE COMPLETE in {mins}m {secs}s")
    print(f"{'='*60}")
    print(f"\n  OUTPUT FILES:")
    print(f"  📊 Excel Report:   {report_path}")
    print(f"  📝 Findings MD:    {findings_path}")
    print(f"  🗂  Raw Data:       {RAW_PATH}")
    print(f"  🔬 Classified:     {CLASSIFIED_PATH}")
    print(f"\n  TOP 3 PRIORITY ISSUES:")
    from src.analyzer import FEATURE_AREA_LABELS
    for i, area in enumerate(results["top3_areas"], 1):
        label = FEATURE_AREA_LABELS.get(area, area)
        row = results["area_stats"][results["area_stats"]["feature_area"] == area].iloc[0]
        print(f"  #{i}: {label} (Vol: {int(row['volume'])}, Score: {row['priority_score']:.1f})")

    print(f"\n  NEXT STEPS:")
    print(f"  1. Review Excel report and validate findings manually")
    print(f"  2. Use findings_*.md as base for the PDF consumer listening report")
    print(f"  3. Post executive summary on LinkedIn with methodology note")
    print(f"  4. Apply to role with link to published report + GitHub repo")
    print()


if __name__ == "__main__":
    main()
