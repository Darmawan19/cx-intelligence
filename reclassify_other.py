import os, json, time, pandas as pd
from pathlib import Path
import anthropic
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
df = pd.read_csv("data/classified_reviews.csv")
other_df = df[df["feature_area"] == "other"].copy()
print(f"Re-classifying {len(other_df)} reviews in 'other' bucket...")

prompt_template = Path("prompts/reclassify_ambiguous.txt").read_text(encoding="utf-8")
BATCH_SIZE = 20
all_results = []

batches = [other_df.iloc[i:i+BATCH_SIZE] for i in range(0, len(other_df), BATCH_SIZE)]
for i, batch in enumerate(batches):
    lines = []
    for _, row in batch.iterrows():
        lines.append(f"[{row['review_index']}] Rating:{row['rating']}★ | {str(row['review_text'])[:300]}")
    reviews_block = "\n".join(lines)
    prompt = prompt_template + "\n\nREVIEWS:\n" + reviews_block
    try:
        resp = client.messages.create(
            model=os.getenv("CLASSIFY_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"): raw = raw.split("```")[1].lstrip("json").strip()
        results = json.loads(raw)
        all_results.extend(results)
        print(f"  Batch {i+1}/{len(batches)} done ({len(results)} classified)")
    except Exception as e:
        print(f"  Batch {i+1} error: {e}")
    time.sleep(0.5)

results_df = pd.DataFrame(all_results)
for col in ["feature_area","issue_type","severity","sentiment","key_phrase","user_impact","has_specific_feature_mention"]:
    if col in results_df.columns:
        df.loc[df["feature_area"] == "other", col] = df.loc[df["feature_area"] == "other", "review_index"].map(
            results_df.set_index("review_index")[col]
        )

df.to_csv("data/classified_reviews.csv", index=False, encoding="utf-8-sig")
print(f"\nDone. New feature_area distribution:")
print(df["feature_area"].value_counts())
