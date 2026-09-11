"""
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

import os
import sys
import time
import csv
from typing import Optional, Dict, Any, List, Union, Tuple
import numpy as np
import cv2

# Ensure src/ is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from preprocessing import preprocess_image
from anomaly_detection import AnomalyDetector, AnomalyResult
from defect_classifier import DefectClassifier, ClassifierResult
from localization import GradCAM, extract_defect_regions
from refinement import RefinementEngine, RefinedInspectionResult
from severity import compute_severity_score, get_severity_color_bgr, RECOMMENDED_ACTIONS


class DefectInspectionPipeline:
    """
    Unified production inspection pipeline coordinating all computer vision
    and deep learning stages for manufacturing quality assurance.
    """
    def __init__(
        self,
        anomaly_approach: str = "autoencoder",
        classifier_backbone: str = "efficientnet_b0",
        device: Optional[str] = None,
        anomaly_threshold: float = 0.035,
        classifier_confidence_threshold: float = 0.70,
        mm_per_pixel: float = 0.12
    ):
        self.mm_per_pixel = mm_per_pixel
        self.anomaly_threshold = anomaly_threshold
        self.classifier_confidence_threshold = classifier_confidence_threshold

        # Stage 1: Anomaly Detector
        self.anomaly_detector = AnomalyDetector(approach=anomaly_approach, device=device)
        self.anomaly_detector.threshold = anomaly_threshold

        # Stage 2: Classifier
        self.defect_classifier = DefectClassifier(backbone=classifier_backbone, device=device)

        # Stage 3: Grad-CAM
        if hasattr(self.defect_classifier, "model") and self.defect_classifier.model is not None:
            self.grad_cam = GradCAM(self.defect_classifier.model)
        else:
            self.grad_cam = None

        # Stage 4: Refinement Engine
        self.refinement_engine = RefinementEngine(
            anomaly_detector=self.anomaly_detector,
            defect_classifier=self.defect_classifier,
            anomaly_threshold=anomaly_threshold,
            classifier_confidence_threshold=classifier_confidence_threshold
        )

    def inspect_image(
        self,
        image_input: Union[str, np.ndarray],
        sample_id: str = "PART_SAMPLE"
    ) -> RefinedInspectionResult:
        """
        Runs the full 5-stage pipeline on an image path or BGR image array.
        """
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image '{image_input}' not found.")
            img_bgr = cv2.imread(image_input)
            if img_bgr is None:
                raise ValueError(f"Could not read image file '{image_input}'.")
        else:
            img_bgr = image_input.copy()

        # 1. Dynamically sync active thresholds from DB settings (Prompt 23)
        try:
            from models import db
            dyn_thresh = db.get_setting("anomaly_threshold")
            if dyn_thresh is not None:
                self.anomaly_detector.threshold = float(dyn_thresh)
                self.refinement_engine.anomaly_threshold = float(dyn_thresh)
            dyn_min_area = db.get_setting("min_defect_area_px")
            if dyn_min_area is not None:
                self.refinement_engine.min_defect_area_px = int(float(dyn_min_area))
        except Exception:
            pass

        # 2. Preprocess
        preprocessed, intermediates = preprocess_image(
            img_bgr,
            target_size=(256, 256),
            apply_roi=True,
            apply_clahe=True,
            apply_denoise=True
        )

        # 3. Grad-CAM Heatmap
        heatmap = None
        if self.grad_cam is not None:
            try:
                import torch
                norm = preprocessed.astype(np.float32) / 255.0
                tensor = torch.from_numpy(norm.transpose(2, 0, 1)).unsqueeze(0).to(self.anomaly_detector.device)
                heatmap = self.grad_cam.generate_heatmap(tensor)
            except Exception:
                heatmap = None

        # 4. Refinement inspection
        res = self.refinement_engine.inspect(
            image=preprocessed,
            sample_id=sample_id,
            heatmap=heatmap,
            mm_per_pixel=self.mm_per_pixel
        )
        return res


# Global singleton pipeline instance for efficient reuse
_GLOBAL_PIPELINE: Optional[DefectInspectionPipeline] = None

def get_pipeline() -> DefectInspectionPipeline:
    global _GLOBAL_PIPELINE
    if _GLOBAL_PIPELINE is None:
        _GLOBAL_PIPELINE = DefectInspectionPipeline()
    return _GLOBAL_PIPELINE


def visualize_inspection_result(
    image: np.ndarray,
    result_dict: Dict[str, Any],
    save_path: Optional[str] = None
) -> np.ndarray:
    """
    Renders high-contrast industrial inspection overlays with severity color codes:
    - Minor: Green (60, 210, 60)
    - Major: Amber (30, 200, 245)
    - Critical: Red (40, 40, 235)
    """
    annotated = cv2.resize(image.copy(), (256, 256))
    h, w = annotated.shape[:2]

    is_defective = result_dict.get("is_defective", False)
    category = result_dict.get("severity_category", "None")
    color = get_severity_color_bgr(category) if is_defective else (50, 200, 50)

    # 1. Top HUD Status Banner
    banner_color = (30, 30, 30)
    cv2.rectangle(annotated, (0, 0), (w, 30), banner_color, -1)

    status_text = (
        f"DEFECT [{category.upper()}]: {result_dict.get('defect_type', 'UNKNOWN').upper()}"
        if is_defective else "PASS: NORMAL (CONFORMING)"
    )
    cv2.putText(annotated, status_text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    conf = result_dict.get("confidence", 0.0)
    conf_str = f"{conf:.1%}"
    cv2.putText(annotated, conf_str, (w - 55, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # 2. Draw Bounding Boxes with Severity Color
    boxes = result_dict.get("bounding_boxes", [])
    for idx, box in enumerate(boxes):
        if isinstance(box, (list, tuple)) and len(box) == 4:
            bx, by, bw, bh = box
        elif isinstance(box, dict):
            bx, by, bw, bh = box.get("x", 0), box.get("y", 0), box.get("width", 0), box.get("height", 0)
        else:
            continue

        cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), color, 2)
        
        # Corner accent notches
        notch = min(6, bw // 3, bh // 3)
        cv2.line(annotated, (bx, by), (bx + notch, by), (255, 255, 255), 2)
        cv2.line(annotated, (bx, by), (bx, by + notch), (255, 255, 255), 2)
        cv2.line(annotated, (bx + bw, by + bh), (bx + bw - notch, by + bh), (255, 255, 255), 2)
        cv2.line(annotated, (bx + bw, by + bh), (bx + bw, by + bh - notch), (255, 255, 255), 2)

        # Region label
        area_mm = result_dict.get("defect_area_mm2", 0.0)
        lbl = f"#{idx+1} {area_mm:.1f}mm2"
        cv2.putText(annotated, lbl, (bx, max(12, by - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA)

    # 3. Bottom Action Banner
    action_text = f"Action: {result_dict.get('recommended_action', 'None')}"
    cv2.rectangle(annotated, (0, h - 22), (w, h), (20, 20, 20), -1)
    cv2.putText(annotated, action_text, (8, h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)

    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        cv2.imwrite(save_path, annotated)

    return annotated


def run_inspection(
    image_input: Union[str, np.ndarray],
    output_dir: str = "outputs",
    save_annotation: bool = True
) -> Dict[str, Any]:
    """
    Main programmatic inspection function required by Prompt 7, 8, 9, 10.

    Args:
        image_input: File path (str) or BGR numpy array [H, W, 3].
        output_dir: Directory where annotated output will be saved.
        save_annotation: If True, saves annotated visualization to disk.

    Returns:
        Structured result dict matching specifications:
        - filename: str
        - is_defective: bool
        - defect_type: str ("normal", "crack", "scratch", etc.)
        - confidence: float
        - bounding_boxes: list of (x, y, w, h)
        - defect_area: float (px)
        - defect_area_mm2: float
        - anomaly_score: float
        - severity_score: float (0 - 100)
        - severity_category: str ("Minor", "Major", "Critical", "None")
        - recommended_action: str ("Log only", "Flag for review", "Reject immediately", etc.)
        - annotated_image_path: str or None
        - annotated_image_bgr: np.ndarray
        - inference_time_ms: float
    """
    start_time = time.time()
    pipeline = get_pipeline()

    if isinstance(image_input, str):
        filename = os.path.basename(image_input)
        sample_id = os.path.splitext(filename)[0]
    else:
        sample_id = f"SAMPLE_{int(time.time() * 1000)}"
        filename = f"{sample_id}.png"

    # Execute full pipeline
    result = pipeline.inspect_image(image_input, sample_id=sample_id)
    inference_ms = round((time.time() - start_time) * 1000.0, 1)

    # Calculate bounding boxes and areas
    boxes: List[Tuple[int, int, int, int]] = []
    total_area_px = 0.0
    total_area_mm2 = 0.0

    if result.decision != "PASS" and result.cleaned_regions:
        for r in result.cleaned_regions:
            boxes.append((r.x, r.y, r.width, r.height))
            total_area_px += r.area_px
            total_area_mm2 += r.area_mm2

    is_defective = (result.decision == "DEFECTIVE") or (result.decision == "REVIEW_REQUIRED")
    defect_type = result.defect_type if is_defective else "normal"

    # Compute Prompt 9 Severity Score
    if is_defective:
        sev_score, sev_category, rec_action = compute_severity_score(
            defect_type=defect_type,
            confidence=result.overall_confidence,
            defect_area_px=total_area_px,
            total_area_px=256.0 * 256.0
        )
    else:
        sev_score = 0.0
        sev_category = "None"
        rec_action = RECOMMENDED_ACTIONS["None"]

    out_dict: Dict[str, Any] = {
        "filename": filename,
        "is_defective": is_defective,
        "decision": result.decision,
        "defect_type": defect_type,
        "confidence": float(round(result.overall_confidence, 4)),
        "bounding_boxes": boxes,
        "defect_area": float(round(total_area_px, 1)),
        "defect_area_mm2": float(round(total_area_mm2, 2)),
        "anomaly_score": float(round(result.anomaly_score, 4)),
        "anomaly_threshold": float(round(result.anomaly_threshold, 4)),
        "severity_score": sev_score,
        "severity_category": sev_category,
        "recommended_action": rec_action,
        "inference_time_ms": inference_ms,
        "is_borderline": result.is_borderline,
        "borderline_reason": result.borderline_reason
    }

    # Generate annotation
    os.makedirs(output_dir, exist_ok=True)
    annotated_path = os.path.join(output_dir, f"inspected_{filename}") if save_annotation else None

    # Use original or letterboxed preprocessed for overlay
    base_img = result.annotated_image if result.annotated_image is not None else np.full((256, 256, 3), 160, dtype=np.uint8)
    annotated = visualize_inspection_result(base_img, out_dict, save_path=annotated_path)

    out_dict["annotated_image_path"] = annotated_path
    out_dict["annotated_image_bgr"] = annotated

    return out_dict


def batch_inspection(
    input_path: Union[str, List[str]],
    output_dir: str = "outputs",
    csv_filename: str = "batch_inspection_summary.csv"
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Runs the pipeline over a folder of test images or a list of image paths,
    saving annotated images and writing a comprehensive summary CSV.
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths: List[str] = []

    if isinstance(input_path, str):
        if os.path.isdir(input_path):
            valid_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
            for root, _, files in os.walk(input_path):
                for f in sorted(files):
                    if os.path.splitext(f.lower())[1] in valid_exts:
                        image_paths.append(os.path.join(root, f))
        elif os.path.isfile(input_path):
            image_paths = [input_path]
    else:
        image_paths = list(input_path)

    if not image_paths:
        print(f"[-] No valid images found in: {input_path}")
        return [], ""

    results: List[Dict[str, Any]] = []
    csv_path = os.path.join(output_dir, csv_filename)

    fieldnames = [
        "filename",
        "is_defective",
        "decision",
        "defect_type",
        "confidence",
        "defect_area_px",
        "defect_area_mm2",
        "anomaly_score",
        "severity_score",
        "severity_category",
        "recommended_action",
        "inference_time_ms",
        "annotated_path"
    ]

    with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for idx, img_path in enumerate(image_paths, 1):
            res = run_inspection(img_path, output_dir=output_dir, save_annotation=True)
            results.append(res)

            writer.writerow({
                "filename": res["filename"],
                "is_defective": res["is_defective"],
                "decision": res["decision"],
                "defect_type": res["defect_type"],
                "confidence": f"{res['confidence']:.4f}",
                "defect_area_px": res["defect_area"],
                "defect_area_mm2": res["defect_area_mm2"],
                "anomaly_score": f"{res['anomaly_score']:.4f}",
                "severity_score": res["severity_score"],
                "severity_category": res["severity_category"],
                "recommended_action": res["recommended_action"],
                "inference_time_ms": res["inference_time_ms"],
                "annotated_path": res.get("annotated_image_path", "")
            })

    return results, csv_path
