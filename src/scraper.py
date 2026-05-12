"""
scraper.py — Step 1 of CX Intelligence Pipeline
Pulls Shopee Indonesia reviews from Google Play Store.

Design decisions:
- Oversample low-rating reviews (1-3★) as they carry richer pain point signal
- Filter to last 6 months for recency
- Deduplicate and clean before saving
"""

import time
import os
import pandas as pd
from datetime import datetime, timedelta
from google_play_scraper import reviews, Sort

APP_ID = os.getenv("APP_ID", "com.shopee.id")


def scrape_reviews(total_count: int = 600, lang: str = "id", country: str = "id") -> pd.DataFrame:
    """
    Scrape Shopee reviews from Google Play.
    
    Sampling strategy:
    - Rating 1★: 30% of total  → richest pain point signal
    - Rating 2★: 25% of total
    - Rating 3★: 20% of total
    - Rating 4★: 15% of total  → helps contrast: what IS working
    - Rating 5★: 10% of total  → baseline for positive framing
    """
    sampling = {1: 0.30, 2: 0.25, 3: 0.20, 4: 0.15, 5: 0.10}
    all_reviews = []

    print(f"\n{'='*60}")
    print(f"[STEP 1 / SCRAPER] Targeting {total_count} reviews for {APP_ID}")
    print(f"{'='*60}")

    for rating, proportion in sampling.items():
        target = int(total_count * proportion)
        print(f"  ⟶ Rating {rating}★ — targeting {target} reviews...")

        try:
            result, _ = reviews(
                APP_ID,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=target,
                filter_score_with=rating
            )
            for r in result:
                r["sampled_rating_bucket"] = rating
            all_reviews.extend(result)
            print(f"    ✓ Got {len(result)} reviews")
        except Exception as e:
            print(f"    ✗ Error on rating {rating}: {e}")

        time.sleep(1.5)  # Polite rate limiting

    if not all_reviews:
        raise RuntimeError("No reviews scraped. Check app ID and network connection.")

    # Build DataFrame
    df = pd.DataFrame(all_reviews)

    # Standardize columns
    col_map = {
        "reviewId": "review_id",
        "userName": "user_name",
        "score": "rating",
        "at": "date",
        "content": "review_text",
        "thumbsUpCount": "thumbs_up",
        "sampled_rating_bucket": "rating_bucket",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    df = df[[c for c in col_map.values() if c in df.columns]]

    # Filter: last 6 months only
    six_months_ago = datetime.now() - timedelta(days=180)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= six_months_ago]

    # Filter: remove empty or very short reviews (< 15 chars = noise)
    df = df[df["review_text"].str.strip().str.len() >= 15]

    # Deduplicate by review_id
    df = df.drop_duplicates(subset="review_id")

    # Sort newest first
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    df["review_index"] = df.index + 1

    print(f"\n[SCRAPER] Done → {len(df)} clean reviews saved")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Rating distribution:")
    for r, count in df["rating"].value_counts().sort_index().items():
        bar = "█" * (count // 5)
        print(f"    {r}★: {count:>3} {bar}")

    return df


def save_raw(df: pd.DataFrame, path: str = "data/raw_reviews.csv") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[SCRAPER] Raw data saved → {path}")
    return path
