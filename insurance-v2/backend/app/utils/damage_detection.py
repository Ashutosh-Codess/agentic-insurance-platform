"""
Vehicle damage assessment for motor claims.

Default path (no trained model present): a real OpenCV technique -- Canny
edge detection followed by edge-pixel density -- used as a proxy for
visible damage (dents/scratches/broken parts create a lot more high-
frequency edge content than an intact panel). This is a legitimate,
commonly-taught computer-vision heuristic, not a random number generator,
but it is still a heuristic: it estimates damage *extent* from edge
texture, not damage *type* or repair cost.

If a trained CNN is available at models/damage_model.h5 (see
utils/vision_model.py + train_damage_model.py), that model's prediction is
used instead and clearly labeled as such in the result.
"""
import cv2
import numpy as np

from app.utils.vision_model import image_to_model_input, load_trained_model


def _edge_density_score(image_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edge_pixel_ratio = float(np.count_nonzero(edges)) / edges.size
    # Empirically, intact vehicle panels rarely exceed ~4-5% edge density;
    # heavily damaged areas commonly show 10%+. Scaled and capped to [0, 1].
    return min(edge_pixel_ratio / 0.15, 1.0)


def assess_vehicle_damage(image_path: str) -> dict:
    image = cv2.imread(image_path)
    if image is None:
        return {"damage_score": 0.0, "method": "none", "reason": "Could not read image file."}

    trained_model = load_trained_model("damage_model.h5")
    if trained_model is not None:
        model_input = image_to_model_input(image)
        prediction = float(trained_model.predict(model_input, verbose=0)[0][0])
        return {
            "damage_score": round(prediction, 2),
            "method": "trained_cnn",
            "reason": "Score from a trained damage-detection CNN.",
        }

    score = _edge_density_score(image)
    return {
        "damage_score": round(score, 2),
        "method": "opencv_edge_density_heuristic",
        "reason": (
            "No trained damage model found -- estimated from edge density via OpenCV "
            "Canny edge detection as a proxy for visible damage extent."
        ),
    }
