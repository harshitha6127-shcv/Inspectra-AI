"""
src/version.py - Application & Model Version Metadata (Prompt 17)
=================================================================
Single source of truth for versioning, release dates, and model architectures.
"""

import os

APP_VERSION = os.environ.get("APP_VERSION", "1.2.0")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "2.1.0")
BUILD_DATE = os.environ.get("BUILD_DATE", "2026-09-10")
API_VERSION = "v1"
PIPELINE_ARCHITECTURE = "CAE Anomaly Detector (SSIM+MSE) + EfficientNet-B0 Classifier + Grad-CAM + Gemini/Multimodal AI"
SUPPORTED_DEFECT_CLASSES = [
    "normal",
    "crack",
    "scratch",
    "dent",
    "stain",
    "discoloration",
    "dimensional_irregularity"
]


def get_version_info() -> dict:
    """Returns application, model, and pipeline architecture metadata."""
    return {
        "app_name": "Vision-Based Defect Detection System",
        "app_version": APP_VERSION,
        "model_version": MODEL_VERSION,
        "api_version": API_VERSION,
        "build_date": BUILD_DATE,
        "architecture": PIPELINE_ARCHITECTURE,
        "supported_classes": SUPPORTED_DEFECT_CLASSES,
        "status": "production_ready"
    }
