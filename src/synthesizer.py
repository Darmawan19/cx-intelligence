"""
synthesizer.py — Step 5 of CX Intelligence Pipeline

For each of the top 3 issue areas:
1. Collect all relevant reviews
2. Send to Claude Sonnet for deep narrative synthesis
3. Return structured research brief per area

Also generates the Executive Summary using the synthesis output.
"""

import os
import pandas as pd
from pathlib import Path
import anthropic
from src.analyzer import FEATURE_AREA_LABELS

SYNTHESIZE_MODEL = os.getenv("SYNTHESIZE_MODEL", "claude-sonnet-4-20250514")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / name
    return prompt_path.read_text(encoding="utf-8")


def _format_reviews_for_synthesis(reviews_df: pd.DataFrame, max_reviews: int = 80) -> str:
    """Format reviews for deep dive prompt — focus on highest severity"""
    top_reviews = reviews_df.nlargest(max_reviews, "severity")
    lines = []
    for _, row in top_reviews.iterrows():
        lines.append(
            f"[Rating: {row['rating']}★ | Severity: {row['severity']} | "
            f"Type: {row.get('issue_type', 'unknown')} | "
            f"Date: {row['date'].strftime('%Y-%m')}]\n"
            f"{row['review_text'][:400]}"
        )
    return "\n\n---\n\n".join(lines)


def synthesize_deep_dives(
    results: dict,
    skip_on_error: bool = True
) -> dict[str, str]:
    """
    Generate deep dive research briefs for top 3 issue areas.
    
    Returns dict mapping feature_area → brief text
    """
    print(f"\n{'='*60}")
    print(f"[STEP 5 / SYNTHESIZER] Generating deep dive briefs")
    print(f"  Model: {SYNTHESIZE_MODEL}")
    print(f"{'='*60}")

    prompt_template = _load_prompt("deep_dive.txt")
    summary = results["summary"]
    area_stats = results["area_stats"]
    top3 = results["top3_areas"]
    top3_reviews = results["top3_reviews"]

    deep_dives = {}

    for i, area in enumerate(top3, 1):
        area_label = FEATURE_AREA_LABELS.get(area, area)
        print(f"\n  [{i}/3] Deep diving: {area_label}...")

        area_data = area_stats[area_stats["feature_area"] == area].iloc[0]
        reviews_df = top3_reviews.get(area, pd.DataFrame())

        if reviews_df.empty:
            print(f"    ⚠ No reviews found for {area}, skipping")
            continue

        reviews_text = _format_reviews_for_synthesis(reviews_df)

        # Fill prompt template
        prompt = (
            prompt_template
            .replace("{{feature_area}}", area)
            .replace("{{feature_area_label}}", area_label)
            .replace("{{total_count}}", str(int(area_data["volume"])))
            .replace("{{avg_severity}}", str(area_data["avg_severity"]))
            .replace("{{pct_of_negative}}", str(area_data["pct_of_negative"]))
            .replace("{{reviews_data}}", reviews_text)
        )

        try:
            response = client.messages.create(
                model=SYNTHESIZE_MODEL,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            brief = response.content[0].text.strip()
            deep_dives[area] = brief
            print(f"    ✓ Brief generated ({len(brief)} chars)")

        except Exception as e:
            print(f"    ✗ Error: {e}")
            if not skip_on_error:
                raise
            deep_dives[area] = f"[Deep dive generation failed for {area_label}: {e}]"

    return deep_dives


def synthesize_executive_summary(results: dict, deep_dives: dict) -> str:
    """Generate executive summary from all analysis data"""
    print(f"\n  Generating Executive Summary...")

    prompt_template = _load_prompt("synthesize_executive.txt")
    summary = results["summary"]
    area_stats = results["area_stats"]
    top3 = results["top3_areas"]

    # Build analysis summary for prompt
    analysis_summary = (
        f"Total reviews analyzed: {summary['total_reviews']}\n"
        f"Date range: {summary['date_range_start']} to {summary['date_range_end']}\n"
        f"Negative reviews: {summary['total_negative']} ({summary['pct_negative']}%)\n"
        f"Overall avg severity: {summary['avg_severity_overall']}/5.0\n"
        f"Source: Google Play Store, Shopee Indonesia (com.shopee.id)"
    )

    top3_summary_lines = []
    for i, area in enumerate(top3[:3], 1):
        row = area_stats[area_stats["feature_area"] == area].iloc[0]
        from src.analyzer import FEATURE_AREA_LABELS
        label = FEATURE_AREA_LABELS.get(area, area)
        top3_summary_lines.append(
            f"#{i}: {label} | Volume: {int(row['volume'])} reviews | "
            f"Avg Severity: {row['avg_severity']}/5 | Priority Score: {row['priority_score']}"
        )

    top3_summary = "\n".join(top3_summary_lines)

    prompt = (
        prompt_template
        .replace("{{analysis_summary}}", analysis_summary)
        .replace("{{top3_summary}}", top3_summary)
    )

    try:
        response = client.messages.create(
            model=SYNTHESIZE_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        exec_summary = response.content[0].text.strip()
        print(f"    ✓ Executive summary generated ({len(exec_summary)} chars)")
        return exec_summary

    except Exception as e:
        print(f"    ✗ Error generating exec summary: {e}")
        return f"[Executive summary generation failed: {e}]"
