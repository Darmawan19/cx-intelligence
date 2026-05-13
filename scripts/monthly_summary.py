"""
scripts/monthly_summary.py

Post-pipeline script: copies the latest findings_*.md into summaries/YYYY-MM.md
and appends a structured entry to MONTHLY_LOG.md.
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path


OUTPUTS_DIR = Path("outputs")
SUMMARIES_DIR = Path("summaries")
LOG_PATH = Path("MONTHLY_LOG.md")
LOG_HEADER = "# Monthly CX Intelligence Log\n\nAutomated monthly run history.\n\n---\n"


def find_latest_findings() -> Path | None:
    pattern = re.compile(r"findings_(\d{8}_\d{4})\.md$")
    candidates = [
        (m.group(1), p)
        for p in OUTPUTS_DIR.glob("findings_*.md")
        if (m := pattern.match(p.name))
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def extract_top3(findings_path: Path) -> list[str]:
    text = findings_path.read_text(encoding="utf-8")
    lines = [l.strip() for l in text.splitlines()]
    top3 = []
    in_matrix = False
    for line in lines:
        if "## Priority Issue Matrix" in line:
            in_matrix = True
            continue
        if in_matrix and line.startswith("|") and not line.startswith("| Rank") and not line.startswith("|---"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                top3.append(parts[1])
            if len(top3) == 3:
                break
        if in_matrix and line.startswith("## ") and "Priority" not in line:
            break
    return top3


def extract_review_count(findings_path: Path) -> int:
    text = findings_path.read_text(encoding="utf-8")
    m = re.search(r"\*\*Reviews analyzed:\*\*\s*([\d,]+)", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


def main():
    SUMMARIES_DIR.mkdir(exist_ok=True)

    findings = find_latest_findings()
    if not findings:
        print("[monthly_summary] No findings_*.md found in outputs/ — skipping.")
        return

    now = datetime.now()
    month_str = now.strftime("%Y-%m")
    run_date = now.strftime("%Y-%m-%d")

    dest = SUMMARIES_DIR / f"{month_str}.md"
    shutil.copy2(findings, dest)
    print(f"[monthly_summary] Copied {findings} → {dest}")

    top3 = extract_top3(findings)
    review_count = extract_review_count(findings)
    top3_str = ", ".join(top3) if top3 else "N/A"

    log_entry = (
        f"## {month_str}\n"
        f"- Run date: {run_date}\n"
        f"- Reviews analyzed: {review_count:,}\n"
        f"- Top 3: {top3_str}\n"
        f"- Report: [summaries/{month_str}.md](summaries/{month_str}.md)\n"
        f"\n"
    )

    if LOG_PATH.exists():
        existing = LOG_PATH.read_text(encoding="utf-8")
        LOG_PATH.write_text(existing + log_entry, encoding="utf-8")
    else:
        LOG_PATH.write_text(LOG_HEADER + "\n" + log_entry, encoding="utf-8")

    print(f"[monthly_summary] Appended entry to {LOG_PATH}")


if __name__ == "__main__":
    main()
