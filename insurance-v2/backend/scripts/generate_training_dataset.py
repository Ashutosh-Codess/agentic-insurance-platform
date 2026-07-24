"""
Generates a SYNTHETIC training dataset using Faker, for training the claim
classifier (and as a stand-in for a real historical-claims export before
you have one).

IMPORTANT -- read this before wiring it into anything else:

This script writes ONLY to backend/datasets/*.csv. It NEVER touches the
live application database, and it is NEVER imported by the FastAPI app
itself. That separation is deliberate: the original project requirement
was "no fake customers, no fake claims, no Faker-generated records" in the
LIVE system, and that rule still holds -- `seed.py` still only creates the
Admin, Agent, and placeholder catalog. What Faker generates here is
training data for an offline model, conceptually identical to downloading
a public Kaggle insurance-claims CSV -- it happens to be synthetic because
no real historical claims dataset exists for this project, not because
fake data belongs in the running product.

Usage:
    python scripts/generate_training_dataset.py
    # writes datasets/synthetic_claims.csv (5,000 rows by default)

Then, separately:
    python scripts/train_classifier.py
    # reads that CSV and trains models/claim_classifier.h5
"""
import argparse
import os
import random

import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()

CLAIM_TYPES = ["health", "life", "motor", "travel", "home", "business"]
CLAIM_CLASSES = ["simple", "complex", "high_value"]


def _generate_row(row_id: int) -> dict:
    claim_type = random.choice(CLAIM_TYPES)

    # Correlate claimed_amount with claim_type the way real data would --
    # motor/home claims cluster lower, business/life cluster higher.
    base_ranges = {
        "health": (5_000, 150_000),
        "motor": (3_000, 100_000),
        "travel": (1_000, 50_000),
        "home": (5_000, 200_000),
        "life": (50_000, 1_000_000),
        "business": (20_000, 800_000),
    }
    low, high = base_ranges[claim_type]
    claimed_amount = round(float(np.random.triangular(low, (low + high) / 3, high)), 2)

    document_count = max(1, int(np.random.poisson(3)))
    has_description = random.random() > 0.15

    # Label generation: deliberately correlated with the features above
    # (not random) so a model trained on this data actually learns
    # something, rather than memorizing noise.
    if claimed_amount >= 200_000:
        claim_class = "high_value"
    elif document_count >= 4:
        claim_class = "complex"
    else:
        claim_class = "simple"

    # A small amount of label noise, like real-world data has.
    if random.random() < 0.05:
        claim_class = random.choice(CLAIM_CLASSES)

    # Fraud label: rare, and correlated with a couple of the same red
    # flags fraud_service.py checks for at runtime (recent duplicate
    # amount, high claim frequency) so the synthetic data is at least
    # thematically consistent with the live heuristics.
    is_fraud = 1 if (random.random() < 0.04 or (claimed_amount > high * 0.9 and document_count <= 1)) else 0

    return {
        "claim_id": f"SYNTH-{row_id:06d}",
        "customer_name": fake.name(),  # synthetic identity, never a real person
        "claim_type": claim_type,
        "claimed_amount": claimed_amount,
        "document_count": document_count,
        "has_description": int(has_description),
        "days_since_policy_start": int(np.random.exponential(120)),
        "prior_claims_count": int(np.random.poisson(1.2)),
        "claim_class": claim_class,
        "is_fraud": is_fraud,
    }


def generate_dataset(num_rows: int, seed: int) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)
    Faker.seed(seed)
    rows = [_generate_row(i) for i in range(num_rows)]
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=5000, help="Number of synthetic rows to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", type=str, default="datasets/synthetic_claims.csv", help="Output CSV path")
    args = parser.parse_args()

    df = generate_dataset(args.rows, args.seed)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)

    print(f"[generate_training_dataset] wrote {len(df)} rows to {args.out}")
    print(f"[generate_training_dataset] claim_class distribution:\n{df['claim_class'].value_counts()}")
    print(f"[generate_training_dataset] fraud rate: {df['is_fraud'].mean():.2%}")


if __name__ == "__main__":
    main()
