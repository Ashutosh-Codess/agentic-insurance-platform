"""
Small Keras model architectures used by the damage-detection and
claim-classification modules.

IMPORTANT, read before assuming this is "fake": these functions build REAL
Keras models and run REAL inference. What they do NOT do is come with
pretrained weights -- there is no labeled vehicle-damage dataset or claims
dataset bundled with this project. `load_trained_model()` looks for a
weights file on disk; if it's not there (which it won't be on a fresh
clone), callers fall back to a deterministic OpenCV/pandas heuristic
instead of running an untrained, meaningless model. Once you train a real
model (see train_damage_model.py for a starter script) and save it to
`models/damage_model.h5`, it is picked up automatically -- no code change
required anywhere else in the project.
"""
import os

import numpy as np
import tensorflow as tf
from tensorflow import keras

MODEL_DIR = os.getenv("MODEL_DIR", "models")


def build_damage_cnn(input_shape: tuple[int, int, int] = (128, 128, 3)) -> keras.Model:
    """A small CNN that maps a vehicle photo to a single damage-severity
    score in [0, 1]. Real architecture, meant to be trained on a labeled
    dataset of vehicle photos with damage-severity labels."""
    model = keras.Sequential(
        [
            keras.layers.Input(shape=input_shape),
            keras.layers.Conv2D(16, 3, activation="relu"),
            keras.layers.MaxPooling2D(),
            keras.layers.Conv2D(32, 3, activation="relu"),
            keras.layers.MaxPooling2D(),
            keras.layers.Flatten(),
            keras.layers.Dense(32, activation="relu"),
            keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["mae"])
    return model


def build_classification_model(num_features: int, num_classes: int) -> keras.Model:
    """A small feedforward network over engineered numeric claim features
    (see services/fraud_service.py and utils/classification.py for the
    feature vector). Meant to be trained on historical, labeled claims."""
    model = keras.Sequential(
        [
            keras.layers.Input(shape=(num_features,)),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(8, activation="relu"),
            keras.layers.Dense(num_classes, activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def load_trained_model(filename: str) -> keras.Model | None:
    """Returns None (never raises) if no trained weights file exists at
    MODEL_DIR/filename -- callers MUST treat None as "use the heuristic
    fallback," exactly like the LLM fallback pattern elsewhere in this
    codebase's design."""
    path = os.path.join(MODEL_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        return keras.models.load_model(path)
    except Exception:
        return None


def image_to_model_input(image_bgr: np.ndarray, size: tuple[int, int] = (128, 128)) -> np.ndarray:
    """Resizes + normalizes an OpenCV BGR image array into the shape the
    damage CNN expects, with a batch dimension of 1."""
    import cv2

    resized = cv2.resize(image_bgr, size)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    normalized = rgb.astype("float32") / 255.0
    return np.expand_dims(normalized, axis=0)
