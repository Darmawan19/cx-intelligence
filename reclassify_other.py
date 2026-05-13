import os
import json
import time
import pandas as pd
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv()

CLASSIFIED_PATH = "data/classified_reviews.csv"
BATCH_SIZE = 20
COLS_TO_UPDATE = [
    "feature_area", "issue_type", "severity", "sentiment",
    "key_phrase", "user_impact", "has_specific_feature_mention",
]


def run(df: pd.DataFrame) -> pd.DataFrame:
    """Re-classify rows where feature_area == 'other'. Returns updated DataFrame."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    prompt_template = Path("prompts/reclassify_ambiguous.txt").read_text(encoding="utf-8")

    other_df = df[df["feature_area"] == "other"].copy()
    print(f"  Re-classifying {len(other_df)} reviews in 'other' bucket...")

    all_results = []
    batches = [other_df.iloc[i:i + BATCH_SIZE] for i in range(0, len(other_df), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        lines = [
            f"[{row['review_index']}] Rating:{row['rating']}★ | {str(row['review_text'])[:300]}"
            for _, row in batch.iterrows()
        ]
        prompt = prompt_template + "\n\nREVIEWS:\n" + "\n".join(lines)
        try:
            resp = client.messages.create(
                model=os.getenv("CLASSIFY_MODEL", "claude-haiku-4-5-20251001"),
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            results = json.loads(raw)
            all_results.extend(results)
            print(f"  Batch {i + 1}/{len(batches)} done ({len(results)} classified)")
        except Exception as e:
            print(f"  Batch {i + 1} error: {e}")
        time.sleep(0.5)

    if all_results:
        results_df = pd.DataFrame(all_results).set_index("review_index")
        for col in COLS_TO_UPDATE:
            if col in results_df.columns:
                mask = df["feature_area"] == "other"
                df.loc[mask, col] = df.loc[mask, "review_index"].map(results_df[col])

    df.to_csv(CLASSIFIED_PATH, index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    df = pd.read_csv(CLASSIFIED_PATH)
    df = run(df)
    print(f"\nDone. New feature_area distribution:")
    print(df["feature_area"].value_counts())
