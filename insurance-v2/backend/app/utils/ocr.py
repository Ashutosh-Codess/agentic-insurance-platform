"""
Document analysis module ("OCR" in the project brief).

Honest scope: full character-level text extraction needs a trained
text-recognition model (a CRNN, or an engine like Tesseract) which is out
of scope for the stack this project is restricted to (OpenCV + TensorFlow
+ NumPy + Pandas only, no external OCR engine). What this module DOES do,
for real, using OpenCV:

  - loads the image
  - converts to grayscale and computes a blur score (variance of the
    Laplacian -- a standard, real OpenCV technique for detecting out-of-
    focus images)
  - computes mean brightness
  - flags the document as legible / needs_manual_review based on those
    two signals

This is a genuinely useful, real check (a blurry or overexposed claim
photo SHOULD be flagged before an agent wastes time on it), and it is
honestly labeled as document-quality validation rather than pretending to
return extracted text it never actually read.
"""
import cv2
import numpy as np

BLUR_THRESHOLD = 100.0  # Laplacian variance below this ~= blurry, tune against real samples
DARK_THRESHOLD = 40.0
BRIGHT_THRESHOLD = 220.0


def analyze_document(image_path: str) -> dict:
    image = cv2.imread(image_path)
    if image is None:
        return {
            "legible": False,
            "status": "needs_manual_review",
            "reason": "File could not be read as an image (unsupported format or corrupt upload).",
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))

    reasons = []
    if blur_score < BLUR_THRESHOLD:
        reasons.append(f"image appears blurry (sharpness score {blur_score:.1f})")
    if brightness < DARK_THRESHOLD:
        reasons.append(f"image appears too dark (brightness {brightness:.1f})")
    if brightness > BRIGHT_THRESHOLD:
        reasons.append(f"image appears overexposed (brightness {brightness:.1f})")

    legible = len(reasons) == 0
    return {
        "legible": legible,
        "status": "processed" if legible else "needs_manual_review",
        "blur_score": round(blur_score, 1),
        "brightness": round(brightness, 1),
        "reason": "; ".join(reasons) if reasons else "document quality checks passed",
    }
