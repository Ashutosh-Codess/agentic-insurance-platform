"""
Claim classification: buckets a claim into "simple" / "complex" /
"high_value" so an agent's queue can be triaged at a glance.

Default path: threshold rules over a small pandas Series of engineered
features (this is a completely reasonable, real technique for a first
version -- classification rules like this are exactly what a lot of
production fraud/triage systems start with before a labeled dataset
exists to train on). If a trained classifier exists at
models/claim_classifier.h5, its prediction is used instead.
"""
import numpy as np
import pandas as pd

from app.utils.vision_model import load_trained_model

CLASSES = ["simple", "complex", "high_value"]

HIGH_VALUE_THRESHOLD = 200_000
COMPLEX_DOC_COUNT_THRESHOLD = 4


def build_feature_vector(claim: dict, document_count: int) -> pd.Series:
    """Small, explicit feature engineering step using pandas -- this is
    the vector a trained model would eventually consume."""
    return pd.Series(
        {
            "claimed_amount": float(claim.get("claimed_amount", 0)),
            "document_count": document_count,
            "has_description": 1 if claim.get("description") else 0,
        }
    )


def classify_claim(claim: dict, document_count: int) -> dict:
    features = build_feature_vector(claim, document_count)

    trained_model = load_trained_model("claim_classifier.h5")
    if trained_model is not None:
        model_input = np.array([features.values], dtype="float32")
        probabilities = trained_model.predict(model_input, verbose=0)[0]
        predicted_class = CLASSES[int(np.argmax(probabilities))]
        return {
            "claim_class": predicted_class,
            "confidence": round(float(np.max(probabilities)), 2),
            "method": "trained_model",
        }

    if features["claimed_amount"] >= HIGH_VALUE_THRESHOLD:
        claim_class = "high_value"
    elif features["document_count"] >= COMPLEX_DOC_COUNT_THRESHOLD:
        claim_class = "complex"
    else:
        claim_class = "simple"

    return {"claim_class": claim_class, "confidence": 0.6, "method": "rule_based"}
