"""Writes a small JSON report per processed claim into REPORTS_DIR. This
is what the `reports/` folder in the project tree is for -- a plain-text
audit trail an agent (or you, marking your own project) can open directly
without querying the database."""
import json
import os
from datetime import datetime, timezone


def write_claim_report(reports_dir: str, claim_id: str, ai_analysis: dict) -> str:
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, f"claim_{claim_id}.json")
    report = {
        "claim_id": claim_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_analysis": ai_analysis,
    }
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return path
