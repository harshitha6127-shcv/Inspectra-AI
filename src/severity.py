"""
src/severity.py - Industrial Defect Severity Scoring Module
============================================================
Evaluates defect impact based on:
1. Defect Area Ratio (% of total inspected surface area)
2. Classifier Confidence (probabilistic certainty)
3. Defect Type Inherent Risk Weight (structural flaws vs cosmetic surface blemishes)

Categorization:
- Minor (<30): Cosmetic or negligible flaw -> Recommended Action: "Log only"
- Major (30-70): Functional risk or notable flaw -> Recommended Action: "Flag for review"
- Critical (>70): Structural failure / out of tolerance -> Recommended Action: "Reject immediately"
"""

from typing import Dict, Tuple, Any, Optional

# Defect inherent risk weights (0.0 to 1.0)
# Structural flaws like cracks or dimensional faults carry highest intrinsic penalty
DEFAULT_SEVERITY_WEIGHTS: Dict[str, float] = {
    "crack": 1.00,                      # High risk: propagation causes catastrophic fatigue
    "dimensional_irregularity": 0.90,   # High risk: out of geometric tolerance/jamming
    "dent": 0.80,                       # Moderate-High: stress concentration / surface breach
    "scratch": 0.55,                    # Moderate: depending on depth/sealing surface
    "stain": 0.35,                      # Low-Moderate: organic/chemical residue
    "discoloration": 0.30,              # Low: cosmetic thermal tint
    "normal": 0.00                      # No defect
}

# Severity Category thresholds
THRESH_MINOR_MAX = 30.0
THRESH_MAJOR_MAX = 70.0

# Color codes in BGR format for OpenCV annotations
SEVERITY_COLORS_BGR = {
    "Minor": (60, 210, 60),      # Green
    "Major": (30, 200, 245),     # Amber / Yellow
    "Critical": (40, 40, 235),   # Red / Crimson
    "None": (180, 180, 180)      # Neutral gray for normal
}

# Color codes in RGB format for Matplotlib and Web UIs
SEVERITY_COLORS_RGB = {
    "Minor": "#22c55e",
    "Major": "#f59e0b",
    "Critical": "#ef4444",
    "None": "#94a3b8"
}

RECOMMENDED_ACTIONS = {
    "Minor": "Log only",
    "Major": "Flag for review",
    "Critical": "Reject immediately",
    "None": "Pass to downstream line"
}


def get_dynamic_thresholds() -> Tuple[float, float]:
    """Dynamically fetches severity cutoffs from database settings if available (Prompt 23)."""
    try:
        from models import db
        minor = float(db.get_setting("severity_minor_cutoff", THRESH_MINOR_MAX))
        major = float(db.get_setting("severity_major_cutoff", THRESH_MAJOR_MAX))
        return minor, major
    except Exception:
        return THRESH_MINOR_MAX, THRESH_MAJOR_MAX


def compute_severity_score(
    defect_type: str,
    confidence: float,
    defect_area_px: float,
    total_area_px: float = 65536.0,  # default 256x256
    custom_weights: Optional[Dict[str, float]] = None,
    minor_cutoff: Optional[float] = None,
    major_cutoff: Optional[float] = None
) -> Tuple[float, str, str]:
    """
    Computes a normalized defect severity score from 0 to 100.

    Formula:
        area_ratio = min(1.0, (defect_area_px / total_area_px) * 15.0) # scaled so 6.6% area = 1.0
        type_weight = weights.get(defect_type, 0.5)
        raw_score = (0.45 * type_weight + 0.35 * area_ratio + 0.20 * confidence) * 100

    Returns:
        (severity_score, severity_category, recommended_action)
    """
    clean_type = defect_type.lower().strip()
    if clean_type == "normal" or defect_area_px <= 0:
        return 0.0, "None", RECOMMENDED_ACTIONS["None"]

    weights = custom_weights or DEFAULT_SEVERITY_WEIGHTS
    type_weight = weights.get(clean_type, 0.50)

    # Area ratio component: defects occupying > 5% of part are severe
    area_ratio = min(1.0, (defect_area_px / max(1.0, total_area_px)) * 18.0)

    # Clamped confidence
    conf = min(1.0, max(0.0, confidence))

    # Weighted composite score (0 to 100)
    score = (
        0.45 * type_weight +
        0.35 * area_ratio +
        0.20 * conf
    ) * 100.0

    score = float(max(0.0, min(100.0, round(score, 1))))

    # Dynamic cutoffs from DB (Prompt 23)
    dyn_minor, dyn_major = get_dynamic_thresholds()
    eff_minor = minor_cutoff if minor_cutoff is not None else dyn_minor
    eff_major = major_cutoff if major_cutoff is not None else dyn_major

    # Map to category
    if score < eff_minor:
        category = "Minor"
    elif score <= eff_major:
        category = "Major"
    else:
        category = "Critical"

    action = RECOMMENDED_ACTIONS[category]
    return score, category, action


def get_severity_color_bgr(category: str) -> Tuple[int, int, int]:
    """Returns the BGR tuple for OpenCV bounding box and text drawing."""
    return SEVERITY_COLORS_BGR.get(category, (255, 255, 255))


def get_severity_color_rgb(category: str) -> str:
    """Returns hex color string for web and matplotlib overlays."""
    return SEVERITY_COLORS_RGB.get(category, "#ffffff")
