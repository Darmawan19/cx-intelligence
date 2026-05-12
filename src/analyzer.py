"""
analyzer.py — Step 4 of CX Intelligence Pipeline

Produces quantitative analysis from classified reviews:
- Volume ranking by feature_area and issue_type
- Severity-weighted priority score
- RICE-inspired prioritization matrix
- Time trend (monthly distribution)
- User impact estimation

This is the "quant" layer that Zefania's role requires.
Answers: "What's highest in volume? What should we prio?"
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime


FEATURE_AREA_LABELS = {
    "checkout_payment": "Checkout & Payment",
    "search_discovery": "Search & Discovery",
    "delivery_logistics": "Delivery & Logistics",
    "seller_experience": "Seller Experience",
    "customer_service": "Customer Service",
    "promotion_voucher": "Promotion & Voucher",
    "app_performance": "App Performance",
    "return_refund": "Return & Refund",
    "account_security": "Account & Security",
    "live_commerce": "Live Commerce",
    "other": "Other / Unclassified",
}

ISSUE_TYPE_LABELS = {
    "bug_crash": "Bug / Crash",
    "ux_confusion": "UX Confusion",
    "slow_performance": "Slow / Lag",
    "misleading_content": "Misleading Content",
    "policy_problem": "Policy Issue",
    "missing_feature": "Missing Feature",
    "pricing_complaint": "Pricing / Fees",
    "positive_experience": "Positive",
    "other": "Other",
}


def compute_priority_score(volume: int, avg_severity: float, widespread_pct: float) -> float:
    """
    Priority Score = Volume × Avg_Severity × (1 + Widespread_Bonus)
    
    Rationale:
    - Volume: how many users affected (Reach in RICE)
    - Avg_Severity: how bad is the impact (Impact in RICE)  
    - Widespread_pct: if many users say it's widespread, weight higher (Confidence)
    - Effort: excluded from scoring (researcher's job is to flag, not estimate fix cost)
    
    This is transparent and defensible in interviews.
    """
    widespread_bonus = widespread_pct * 0.5  # Max 50% bonus
    return round(volume * avg_severity * (1 + widespread_bonus), 2)


def analyze(df: pd.DataFrame) -> dict:
    """
    Main analysis function. Returns a dict with all tables and insights.
    """
    print(f"\n{'='*60}")
    print(f"[STEP 4 / ANALYZER] Running statistical analysis")
    print(f"  Total reviews: {len(df)}")
    print(f"{'='*60}")

    # Separate negative from all reviews for percentage calc
    negative_mask = df["sentiment"].isin(["negative", "very_negative"])
    negative_df = df[negative_mask]
    total_negative = len(negative_df)

    print(f"  Negative reviews: {total_negative} ({total_negative/len(df)*100:.1f}%)")
    print(f"  Avg severity (all): {df['severity'].mean():.2f}")

    # ─── TABLE 1: Feature Area Summary ───────────────────────────────────────
    print("\n  Building feature area ranking...")

    area_stats = (
        df.groupby("feature_area")
        .agg(
            volume=("review_id", "count"),
            avg_severity=("severity", "mean"),
            pct_widespread=(
                "user_impact",
                lambda x: (x == "likely_widespread").mean()
            ),
            pct_negative=(
                "sentiment",
                lambda x: x.isin(["negative", "very_negative"]).mean()
            ),
            avg_rating=("rating", "mean"),
        )
        .reset_index()
    )

    area_stats["priority_score"] = area_stats.apply(
        lambda r: compute_priority_score(
            r["volume"], r["avg_severity"], r["pct_widespread"]
        ), axis=1
    )
    area_stats["pct_of_total"] = (area_stats["volume"] / len(df) * 100).round(1)
    area_stats["pct_of_negative"] = (area_stats["volume"] / max(total_negative, 1) * 100).round(1)
    area_stats["label"] = area_stats["feature_area"].map(FEATURE_AREA_LABELS)
    area_stats["avg_severity"] = area_stats["avg_severity"].round(2)
    area_stats["pct_widespread"] = (area_stats["pct_widespread"] * 100).round(1)
    area_stats["pct_negative"] = (area_stats["pct_negative"] * 100).round(1)
    area_stats["avg_rating"] = area_stats["avg_rating"].round(2)
    area_stats = area_stats.sort_values("priority_score", ascending=False).reset_index(drop=True)
    area_stats["rank"] = area_stats.index + 1

    # ─── TABLE 2: Issue Type Breakdown ───────────────────────────────────────
    print("  Building issue type breakdown...")

    issue_stats = (
        df.groupby(["feature_area", "issue_type"])
        .agg(
            volume=("review_id", "count"),
            avg_severity=("severity", "mean"),
        )
        .reset_index()
    )
    issue_stats["avg_severity"] = issue_stats["avg_severity"].round(2)
    issue_stats["feature_label"] = issue_stats["feature_area"].map(FEATURE_AREA_LABELS)
    issue_stats["issue_label"] = issue_stats["issue_type"].map(ISSUE_TYPE_LABELS)
    issue_stats = issue_stats.sort_values(["feature_area", "volume"], ascending=[True, False])

    # ─── TABLE 3: Monthly Trend ───────────────────────────────────────────────
    print("  Building monthly trend...")

    df["month"] = df["date"].dt.to_period("M").astype(str)
    trend = (
        df[negative_mask]
        .groupby(["month", "feature_area"])
        .agg(volume=("review_id", "count"))
        .reset_index()
    )
    trend["label"] = trend["feature_area"].map(FEATURE_AREA_LABELS)

    # ─── TABLE 4: Severity Distribution ──────────────────────────────────────
    severity_dist = (
        df.groupby("severity")
        .agg(count=("review_id", "count"))
        .reset_index()
    )
    severity_dist["pct"] = (severity_dist["count"] / len(df) * 100).round(1)

    # ─── TABLE 5: Sentiment Distribution ─────────────────────────────────────
    sentiment_dist = (
        df.groupby("sentiment")
        .agg(count=("review_id", "count"))
        .reset_index()
    )
    sentiment_dist["pct"] = (sentiment_dist["count"] / len(df) * 100).round(1)

    # ─── TOP 3 — for deep dive ────────────────────────────────────────────────
    # Exclude "other" and "positive_experience" from top 3
    meaningful = area_stats[
        ~area_stats["feature_area"].isin(["other"])
    ]
    top3_areas = meaningful.head(3)["feature_area"].tolist()

    top3_reviews = {}
    for area in top3_areas:
        area_reviews = df[
            (df["feature_area"] == area) &
            (df["sentiment"].isin(["negative", "very_negative", "mixed"]))
        ].sort_values("severity", ascending=False)
        top3_reviews[area] = area_reviews

    # ─── Summary Stats ────────────────────────────────────────────────────────
    summary = {
        "total_reviews": len(df),
        "total_negative": total_negative,
        "pct_negative": round(total_negative / len(df) * 100, 1),
        "avg_severity_overall": round(df["severity"].mean(), 2),
        "date_range_start": df["date"].min().strftime("%Y-%m-%d"),
        "date_range_end": df["date"].max().strftime("%Y-%m-%d"),
        "top3_areas": top3_areas,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # Print top areas
    print(f"\n  📊 TOP ISSUE AREAS BY PRIORITY SCORE:")
    print(f"  {'Rank':<4} {'Area':<25} {'Vol':>5} {'AvgSev':>7} {'Score':>8}")
    print(f"  {'-'*55}")
    for _, row in area_stats.head(6).iterrows():
        print(
            f"  {int(row['rank']):<4} {row['label']:<25} "
            f"{int(row['volume']):>5} {row['avg_severity']:>7.2f} "
            f"{row['priority_score']:>8.1f}"
        )

    results = {
        "summary": summary,
        "area_stats": area_stats,
        "issue_stats": issue_stats,
        "trend": trend,
        "severity_dist": severity_dist,
        "sentiment_dist": sentiment_dist,
        "top3_areas": top3_areas,
        "top3_reviews": top3_reviews,
        "df": df,
    }

    print(f"\n[ANALYZER] Done → Top 3 areas for deep dive: {top3_areas}")
    return results


def save_analysis(results: dict, path: str = "data/analysis_results.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    results["area_stats"].to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[ANALYZER] Saved area stats → {path}")
    return path
