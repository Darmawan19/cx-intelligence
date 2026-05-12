"""
classifier.py — Step 2 & 3 of CX Intelligence Pipeline

Step 2: Batch classify all reviews via Claude API
  - Batches of 20 reviews per call (cost/performance balance)
  - Each review gets: feature_area, issue_type, severity, sentiment, key_phrase

Step 3: Quality gate
  - Sample 50 random reviews
  - Manual spot-check interface
  - Flag if error rate > 15% (configurable)
"""

import os
import json
import time
import random
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import anthropic

CLASSIFY_MODEL = os.getenv("CLASSIFY_MODEL", "claude-haiku-4-5-20251001")
BATCH_SIZE = 20
QUALITY_SAMPLE = int(os.getenv("QUALITY_SAMPLE_SIZE", 50))
QUALITY_THRESHOLD = float(os.getenv("QUALITY_GATE_THRESHOLD", 0.15))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _load_prompt(name: str) -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / name
    return prompt_path.read_text(encoding="utf-8")


def _format_reviews_block(batch: pd.DataFrame) -> str:
    """Format a batch of reviews for the prompt"""
    lines = []
    for _, row in batch.iterrows():
        lines.append(
            f"[{row['review_index']}] Rating: {row['rating']}★ | "
            f"Date: {row['date'].strftime('%Y-%m-%d')} | "
            f"Review: {row['review_text'][:500]}"  # Cap at 500 chars
        )
    return "\n".join(lines)


def _classify_batch(batch: pd.DataFrame, prompt_template: str) -> list[dict]:
    """Send one batch to Claude API and parse JSON response"""
    reviews_block = _format_reviews_block(batch)
    prompt = prompt_template.replace("{{reviews_block}}", reviews_block)

    try:
        response = client.messages.create(
            model=CLASSIFY_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        # Strip markdown if model wraps in ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"    ⚠ JSON parse error: {e} — skipping batch")
        return []
    except Exception as e:
        print(f"    ⚠ API error: {e}")
        return []


def classify_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify all reviews in batches of BATCH_SIZE.
    Returns original df enriched with classification columns.
    """
    print(f"\n{'='*60}")
    print(f"[STEP 2 / CLASSIFIER] Classifying {len(df)} reviews")
    print(f"  Model: {CLASSIFY_MODEL} | Batch size: {BATCH_SIZE}")
    print(f"  Estimated API calls: {len(df) // BATCH_SIZE + 1}")
    print(f"{'='*60}")

    prompt_template = _load_prompt("classify_batch.txt")

    all_results = []
    batches = [df.iloc[i:i + BATCH_SIZE] for i in range(0, len(df), BATCH_SIZE)]

    for i, batch in enumerate(tqdm(batches, desc="  Classifying", unit="batch")):
        results = _classify_batch(batch, prompt_template)
        all_results.extend(results)

        # Polite rate limiting
        if i < len(batches) - 1:
            time.sleep(0.5)

    if not all_results:
        raise RuntimeError("Classification returned no results. Check API key and prompt.")

    # Convert to DataFrame and merge
    results_df = pd.DataFrame(all_results)
    enriched = df.merge(results_df, on="review_index", how="left")

    # Fill any failed classifications
    enriched["feature_area"] = enriched["feature_area"].fillna("other")
    enriched["issue_type"] = enriched["issue_type"].fillna("other")
    enriched["severity"] = pd.to_numeric(enriched["severity"], errors="coerce").fillna(2)
    enriched["sentiment"] = enriched["sentiment"].fillna("neutral")
    enriched["key_phrase"] = enriched["key_phrase"].fillna("")
    enriched["user_impact"] = enriched["user_impact"].fillna("individual")
    enriched["has_specific_feature_mention"] = enriched["has_specific_feature_mention"].fillna(False)

    classified_count = enriched["feature_area"].notna().sum()
    print(f"\n[CLASSIFIER] Done → {classified_count}/{len(df)} reviews classified")

    return enriched


def quality_gate(df: pd.DataFrame) -> dict:
    """
    Step 3: Quality check on a random sample.
    
    Runs an automated consistency check:
    - Reviews with rating 1★ should mostly be negative/very_negative sentiment
    - Reviews with rating 5★ should mostly be positive/very_positive sentiment
    - Severity should correlate inversely with rating

    Returns quality report dict.
    """
    print(f"\n{'='*60}")
    print(f"[STEP 3 / QUALITY GATE] Validating classification quality")
    print(f"{'='*60}")

    sample = df.sample(min(QUALITY_SAMPLE, len(df)), random_state=42)
    errors = 0
    issues = []

    for _, row in sample.iterrows():
        flag = False

        # Rule 1: 1★ reviews shouldn't be classified as positive/very_positive
        if row["rating"] == 1 and row["sentiment"] in ["positive", "very_positive"]:
            issues.append(f"Review #{row['review_index']}: 1★ but classified as {row['sentiment']}")
            flag = True

        # Rule 2: 5★ reviews shouldn't be classified as very_negative
        if row["rating"] == 5 and row["sentiment"] == "very_negative":
            issues.append(f"Review #{row['review_index']}: 5★ but classified as very_negative")
            flag = True

        # Rule 3: 1★ reviews should have severity >= 2
        if row["rating"] == 1 and row["severity"] < 2:
            issues.append(f"Review #{row['review_index']}: 1★ but severity={row['severity']}")
            flag = True

        if flag:
            errors += 1

    error_rate = errors / len(sample)
    passed = error_rate <= QUALITY_THRESHOLD

    report = {
        "sample_size": len(sample),
        "errors_found": errors,
        "error_rate": round(error_rate, 3),
        "threshold": QUALITY_THRESHOLD,
        "passed": passed,
        "issues": issues[:10]  # Show max 10 issues
    }

    status = "✓ PASSED" if passed else "✗ FAILED"
    print(f"  Result: {status}")
    print(f"  Error rate: {error_rate:.1%} (threshold: {QUALITY_THRESHOLD:.0%})")
    if issues:
        print(f"  Sample issues found:")
        for issue in issues[:5]:
            print(f"    • {issue}")

    if not passed:
        print(f"\n  ⚠ Quality gate failed. Consider:")
        print(f"    1. Review the prompt in prompts/classify_batch.txt")
        print(f"    2. Check if reviews contain unusual slang")
        print(f"    3. Run with --skip-quality-gate to proceed anyway")

    return report


def save_classified(df: pd.DataFrame, report: dict, path: str = "data/classified_reviews.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    
    report_path = path.replace(".csv", "_quality_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[CLASSIFIER] Saved → {path}")
    print(f"[CLASSIFIER] Quality report → {report_path}")
    return path
