export interface CodeFileMeta {
  path: string;
  name: string;
  stage: string;
  description: string;
  code: string;
}

export const PROJECT_CODE_FILES: CodeFileMeta[] = [
  {
    path: "src/severity.py",
    name: "severity.py",
    stage: "Prompt 9",
    description: "Defect severity scoring (0-100), Minor/Major/Critical categorization, action recommendations, and color codes.",
    code: `"""
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

DEFAULT_SEVERITY_WEIGHTS: Dict[str, float] = {
    "crack": 1.00,                      # High risk: propagation causes catastrophic fatigue
    "dimensional_irregularity": 0.90,   # High risk: out of geometric tolerance/jamming
    "dent": 0.80,                       # Moderate-High: stress concentration / surface breach
    "scratch": 0.55,                    # Moderate: depending on depth/sealing surface
    "stain": 0.35,                      # Low-Moderate: organic/chemical residue
    "discoloration": 0.30,              # Low: cosmetic thermal tint
    "normal": 0.00                      # No defect
}

THRESH_MINOR_MAX = 30.0
THRESH_MAJOR_MAX = 70.0

SEVERITY_COLORS_BGR = {
    "Minor": (60, 210, 60),      # Green
    "Major": (30, 200, 245),     # Amber / Yellow
    "Critical": (40, 40, 235),   # Red / Crimson
    "None": (180, 180, 180)
}

RECOMMENDED_ACTIONS = {
    "Minor": "Log only",
    "Major": "Flag for review",
    "Critical": "Reject immediately",
    "None": "Pass to downstream line"
}

def compute_severity_score(defect_type, confidence, defect_area_px, total_area_px=65536.0, custom_weights=None):
    clean_type = defect_type.lower().strip()
    if clean_type == "normal" or defect_area_px <= 0:
        return 0.0, "None", RECOMMENDED_ACTIONS["None"]

    weights = custom_weights or DEFAULT_SEVERITY_WEIGHTS
    type_weight = weights.get(clean_type, 0.50)
    area_ratio = min(1.0, (defect_area_px / max(1.0, total_area_px)) * 18.0)
    conf = min(1.0, max(0.0, confidence))

    score = (0.45 * type_weight + 0.35 * area_ratio + 0.20 * conf) * 100.0
    score = float(max(0.0, min(100.0, round(score, 1))))

    if score < THRESH_MINOR_MAX:
        category = "Minor"
    elif score <= THRESH_MAJOR_MAX:
        category = "Major"
    else:
        category = "Critical"

    return score, category, RECOMMENDED_ACTIONS[category]`
  },
  {
    path: "src/evaluate.py",
    name: "evaluate.py",
    stage: "Prompt 6",
    description: "Accuracy, Precision, Recall, F1, ROC-AUC, per-class metrics, mask IoU (mIoU), curves, and text report.",
    code: `"""
src/evaluate.py - Quantitative Evaluation & Model Metrics Module
================================================================
Prompt 6 Implementation:
1. Computes Accuracy, Precision, Recall, F1-Score, and ROC-AUC for Defective/Normal detection.
2. Computes Per-Class Precision/Recall/F1 for all 7 defect classes + Macro and Weighted F1.
3. Computes pixel-level Intersection over Union (IoU) and Mean IoU (mIoU) for localization.
4. Generates publication-ready plots:
   - outputs/roc_curve.png
   - outputs/precision_recall_curve.png
   - outputs/confusion_matrix.png
5. Compiles and saves single comprehensive report to outputs/evaluation_report.txt.
"""
import os, sys, time, numpy as np, cv2

def compute_mask_iou(pred_mask, gt_mask):
    pred_bin = (pred_mask > 0).astype(bool)
    gt_bin = (gt_mask > 0).astype(bool)
    intersection = np.logical_and(pred_bin, gt_bin).sum()
    union = np.logical_or(pred_bin, gt_bin).sum()
    if union == 0:
        return 1.0 if not pred_bin.any() and not gt_bin.any() else 0.0
    return float(intersection) / float(union)

def run_evaluation(samples_per_class=15, output_dir="outputs"):
    # Runs evaluation pipeline over test benchmark and outputs summary report
    pass`
  },
  {
    path: "src/pipeline.py",
    name: "pipeline.py",
    stage: "Prompt 7",
    description: "Unified end-to-end pipeline with run_inspection(), batch_inspection(), and severity-coded visualization.",
    code: `"""
src/pipeline.py - Unified End-to-End Industrial Inspection Pipeline
===================================================================
Chains:
1. Preprocessing & Normalization (CLAHE, Bilateral, ROI, Letterboxing)
2. Anomaly Detection (Convolutional Autoencoder / CNN)
3. Multi-Class Defect Classifier (EfficientNet-B0)
4. Localization (Grad-CAM & Contours)
5. Refinement (Consensus, Morphological filter, TTA)
6. Severity Scoring (Minor / Major / Critical, Actions & Color codes)

Exposes:
- run_inspection(image_path) -> Dict[str, Any]
- visualize_inspection_result(image, result, save_path)
- batch_inspection(folder_or_list, output_dir)
"""
import os, sys, time, csv, numpy as np, cv2
from severity import compute_severity_score, get_severity_color_bgr

def run_inspection(image_input, output_dir="outputs", save_annotation=True):
    # Loads image -> preprocesses -> anomaly detection -> classification + localization -> refinement -> severity
    pass

def batch_inspection(input_path, output_dir="outputs", csv_filename="batch_inspection_summary.csv"):
    # Runs batch inspection and outputs CSV summary table
    pass`
  },
  {
    path: "main.py",
    name: "main.py",
    stage: "Prompt 7",
    description: "Command line interface: python main.py --input path/to/image_or_folder, --evaluate, --demo.",
    code: `#!/usr/bin/env python3
"""
main.py - Vision-Based Defect Detection CLI Master Entry Point
=============================================================
Supports:
1. Direct inspection of image or folder (Prompt 7):
   python main.py --input path/to/image_or_folder

2. Quantitative evaluation & benchmarking (Prompt 6):
   python main.py --evaluate --samples 15

3. End-to-end demo batch simulation:
   python main.py --demo

4. Dataset preparation (Prompt 0):
   python main.py prepare --source synthetic --samples 50
"""
import os, sys, argparse
from pipeline import run_inspection, batch_inspection
from evaluate import run_evaluation

def main():
    parser = argparse.ArgumentParser(description="Vision-Based Defect Detection System")
    parser.add_argument("--input", type=str, default=None, help="Path to input image file or folder")
    parser.add_argument("--evaluate", action="store_true", help="Run quantitative evaluation (Prompt 6)")
    parser.add_argument("--demo", action="store_true", help="Run demo batch simulation")
    args = parser.parse_args()
    # Route execution accordingly
    pass`
  },
  {
    path: "src/app.py",
    name: "app.py",
    stage: "Prompt 8 & 10",
    description: "Flask backend serving web dashboard (/), live camera stream (/live), POST /analyze, and GET /report/<batch_id>.",
    code: `"""
src/app.py - Flask Web Application for Defect Detection & Live Inspection
=========================================================================
Implements:
- Prompt 8: Single-page image upload & reporting web interface
- Prompt 10: Browser-based live camera inspection stream (/live route)
"""
from flask import Flask, request, jsonify, render_template, send_file
from pipeline import run_inspection

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 # 10MB limit

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/live")
def live():
    return render_template("live.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    # Accepts images, calls run_inspection(), returns base64 annotated image & telemetry
    pass

@app.route("/report/<batch_id>")
def download_report(batch_id):
    # Returns downloadable batch CSV report
    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)`
  },
  {
    path: "src/live_inspection.py",
    name: "live_inspection.py",
    stage: "Prompt 10",
    description: "Local OpenCV webcam inspector with continuous interval (2s), 'c' keypress, and HUD overlay.",
    code: `"""
src/live_inspection.py - Local OpenCV Live Camera Feed Inspection Script
========================================================================
Prompt 10 Implementation:
1. Opens local optical camera sensor via cv2.VideoCapture.
2. Evaluates frames automatically every N seconds (default 2s) or on keypress ('c').
3. Runs frame through run_inspection() and overlays defect status, severity, confidence, and boxes.
4. Includes simulated test mode (--simulate) for headless or container environments.
"""
import cv2, time, argparse
from pipeline import run_inspection

def run_live_inspection(camera_index=0, interval_sec=2.0, simulate=False):
    cap = cv2.VideoCapture(camera_index)
    # Loop grabbing frames and rendering inspection HUD overlay
    pass`
  },
  {
    path: "requirements.txt",
    name: "requirements.txt",
    stage: "Prompt 0",
    description: "Core PyTorch, OpenCV, Albumentations, scikit-learn, and Flask dependencies.",
    code: `# Vision-Based Defect Detection for Manufacturing Quality Inspection
torch>=2.0.0
torchvision>=0.15.0
opencv-python>=4.8.0
albumentations>=1.3.1
scikit-image>=0.21.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
seaborn>=0.12.0
pandas>=2.0.0
flask>=2.3.0
werkzeug>=2.3.0`
  }
];
