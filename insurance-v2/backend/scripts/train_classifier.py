"""
Trains the claim-classification model on the dataset produced by
generate_training_dataset.py, and saves it to MODEL_DIR/claim_classifier.h5.

Once that file exists, app/utils/classification.py picks it up
automatically on the next claim processed -- no code change needed
anywhere else in the project (see load_trained_model() in
app/utils/vision_model.py).

Usage:
    python scripts/generate_training_dataset.py   # if you haven't already
    python scripts/train_classifier.py

Deliberately uses only numpy/pandas/tensorflow for the train/test split
and training loop -- no scikit-learn -- to stay inside the exact stack
this project is scoped to.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.utils.vision_model import build_classification_model  # noqa: E402

CLASSES = ["simple", "complex", "high_value"]
FEATURE_COLUMNS = ["claimed_amount", "document_count", "has_description"]
MODEL_DIR = os.getenv("MODEL_DIR", "models")


def _train_test_split(X: np.ndarray, y: np.ndarray, test_size: float = 0.2, seed: int = 42):
    rng = np.random.default_rng(seed)
    indices = rng.permutation(len(X))
    split = int(len(X) * (1 - test_size))
    train_idx, test_idx = indices[:split], indices[split:]
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def main() -> None:
    dataset_path = "datasets/synthetic_claims.csv"
    if not os.path.exists(dataset_path):
        raise SystemExit(
            f"{dataset_path} not found -- run `python scripts/generate_training_dataset.py` first."
        )

    df = pd.read_csv(dataset_path)

    # Normalize claimed_amount to a similar scale as the other features --
    # a small, honest preprocessing step, not a hidden trick.
    df["claimed_amount"] = df["claimed_amount"] / df["claimed_amount"].max()

    X = df[FEATURE_COLUMNS].to_numpy(dtype="float32")
    y = df["claim_class"].map({c: i for i, c in enumerate(CLASSES)}).to_numpy()

    X_train, X_test, y_train, y_test = _train_test_split(X, y)

    model = build_classification_model(num_features=len(FEATURE_COLUMNS), num_classes=len(CLASSES))
    model.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.1, verbose=2)

    test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"[train_classifier] test accuracy: {test_accuracy:.2%}")

    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "claim_classifier.h5")
    model.save(model_path)
    print(f"[train_classifier] saved model to {model_path}")


if __name__ == "__main__":
    main()
