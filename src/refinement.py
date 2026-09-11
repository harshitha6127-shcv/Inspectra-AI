"""
refinement.py - Stage 4: False Positive Reduction & Industrial Robustness
========================================================================
Implements multi-layer verification to eliminate false alarms and false escapes:
1. Dual-Model Confidence Consensus:
   - Requires agreement between Anomaly Detector (reconstruction error)
     and Multi-class Classifier (defect category confidence).
2. Morphological Mask Conditioning:
   - Morphological opening/closing removes sensor speckle, dust, and grain noise.
   - Enforces minimum defect area thresholds.
3. Test-Time Augmentation (TTA) Ensemble Voting:
   - Evaluates part across multiple spatial orientations (Original, Horizontal Flip, Slight Rotation).
   - Confirms persistent physical defects while rejecting transient lighting glares.
4. Borderline Quarantine Logging:
   - Flags low-margin or conflicting decisions for secondary manual QA review.
   - Exports structured JSON/CSV inspection manifests.
"""

import os
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional, Any, Union
import numpy as np
import cv2

from anomaly_detection import AnomalyDetector, AnomalyResult
from defect_classifier import DefectClassifier, ClassifierResult
from localization import extract_defect_regions, DefectRegion, overlay_localization_result


@dataclass
class TTAPrediction:
    view_name: str
    predicted_class: str
    confidence: float
    anomaly_score: float


@dataclass
class BorderlineLogEntry:
    timestamp: str
    sample_id: str
    status: str                       # "QUARANTINED_FOR_REVIEW", "PASSED", "REJECTED_DEFECTIVE"
    final_decision: str              # "normal" or defect type
    dual_agreement: bool
    anomaly_score: float
    anomaly_threshold: float
    classifier_class: str
    classifier_confidence: float
    tta_votes: Dict[str, int]
    reason: str


@dataclass
class RefinedInspectionResult:
    decision: str                      # "PASS", "DEFECTIVE", "REVIEW_REQUIRED"
    defect_type: str                   # e.g., "crack", "scratch", "normal"
    overall_confidence: float          # Calibrated confidence score [0.0, 1.0]
    is_borderline: bool                # Whether human operator review is flagged
    dual_model_agreed: bool            # True if both anomaly detector & classifier agreed
    anomaly_result: AnomalyResult
    classifier_result: ClassifierResult
    tta_predictions: List[TTAPrediction]
    cleaned_regions: List[DefectRegion]
    annotated_image: np.ndarray        # High-res overlay image ready for operator screen


class RefinementEngine:
    """
    Robustness and decision-making engine combining dual-model voting,
    morphological cleanup, TTA inference, and borderline quarantine logging.
    """
    def __init__(
        self,
        anomaly_detector: AnomalyDetector,
        defect_classifier: DefectClassifier,
        anomaly_threshold: float = 0.035,
        classifier_confidence_threshold: float = 0.70,
        borderline_margin: float = 0.12,
        min_defect_area_px: int = 25,
        log_file: str = "outputs/borderline_review_queue.json"
    ):
        self.anomaly_detector = anomaly_detector
        self.defect_classifier = defect_classifier
        self.anomaly_threshold = anomaly_threshold
        self.classifier_confidence_threshold = classifier_confidence_threshold
        self.borderline_margin = borderline_margin
        self.min_defect_area_px = min_defect_area_px
        self.log_file = log_file

    def apply_morphological_filtering(
        self,
        binary_mask: np.ndarray,
        kernel_size: int = 3
    ) -> np.ndarray:
        """
        Cleans binary defect mask to reject dust, grain, and high-frequency noise.
        1. Morphological Opening (Erosion -> Dilation): Eradicates isolated speckles.
        2. Morphological Closing (Dilation -> Erosion): Bridges micro-fractures in cracks.
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        # 1. Opening removes small isolated bright spots (salt noise / dust)
        opened = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        # 2. Closing bridges tiny gaps along fissures
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)
        return closed

    def run_test_time_augmentation(
        self,
        image: np.ndarray
    ) -> Tuple[List[TTAPrediction], str, float]:
        """
        Executes Test-Time Augmentation (TTA):
        Evaluates:
          1. Original Canonical Orientation
          2. Horizontal Flip
          3. +10 Degree Rotation
        
        Returns:
            tta_results: List of individual view predictions.
            consensus_class: Plurality voted class.
            mean_conf: Average confidence across views.
        """
        h, w = image.shape[:2]
        views = [
            ("Original", image),
            ("Horizontal_Flip", cv2.flip(image, 1)),
        ]
        
        # Add 10-degree rotated view
        rot_matrix = cv2.getRotationMatrix2D((w // 2, h // 2), 10, 1.0)
        rotated = cv2.warpAffine(image, rot_matrix, (w, h), borderMode=cv2.BORDER_REFLECT_101)
        views.append(("Rotated_+10deg", rotated))

        tta_results: List[TTAPrediction] = []
        votes: Dict[str, int] = {}
        confidences: List[float] = []

        for view_name, v_img in views:
            anom_res = self.anomaly_detector.predict(v_img)
            clf_res = self.defect_classifier.predict(v_img)

            # Determine view verdict
            pred_c = clf_res.predicted_class
            if anom_res.label == "normal" and clf_res.confidence < self.classifier_confidence_threshold:
                pred_c = "normal"

            votes[pred_c] = votes.get(pred_c, 0) + 1
            confidences.append(clf_res.confidence)

            tta_results.append(TTAPrediction(
                view_name=view_name,
                predicted_class=pred_c,
                confidence=clf_res.confidence,
                anomaly_score=anom_res.anomaly_score
            ))

        # Plurality voting consensus
        consensus_class = max(votes, key=votes.get)
        mean_conf = float(np.mean(confidences))
        return tta_results, consensus_class, mean_conf

    def log_borderline_case(self, entry: BorderlineLogEntry):
        """Appends borderline or conflicted inspection case to manual QA audit queue."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        entries = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r") as f:
                    entries = json.load(f)
            except Exception:
                entries = []

        entries.append(asdict(entry))
        with open(self.log_file, "w") as f:
            json.dump(entries, f, indent=2)

    def inspect(
        self,
        image: np.ndarray,
        sample_id: str = "PART_SAMPLE_001",
        heatmap: Optional[np.ndarray] = None,
        mm_per_pixel: float = 0.12
    ) -> RefinedInspectionResult:
        """
        Executes end-to-end refined inspection on a manufactured part image.

        Rules:
        1. Run Anomaly Detector and Defect Classifier.
        2. Verify Dual-Model Consensus.
        3. Run TTA Voting Ensemble.
        4. Apply Morphological Noise Filtering on defect regions.
        5. Check Borderline Review thresholds and log if necessary.
        """
        # Step 1: Base Model Inferences
        anom_res = self.anomaly_detector.predict(image)
        clf_res = self.defect_classifier.predict(image)

        # Step 2: Test-Time Augmentation
        tta_results, consensus_class, tta_conf = self.run_test_time_augmentation(image)
        tta_vote_counts = {}
        for p in tta_results:
            tta_vote_counts[p.predicted_class] = tta_vote_counts.get(p.predicted_class, 0) + 1

        # Step 3: Dual-Model Consensus Evaluation
        detector_flags_defect = anom_res.anomaly_score >= self.anomaly_threshold
        classifier_flags_defect = (
            clf_res.predicted_class != "normal" and
            clf_res.confidence >= self.classifier_confidence_threshold
        )

        dual_agreement = (detector_flags_defect == classifier_flags_defect)

        # Step 4: Morphological Filtering on Defect Heatmap/Mask
        if heatmap is None:
            # Derive difference map or synthetic localization from CAE reconstruction
            if anom_res.diff_map is not None:
                diff = anom_res.diff_map.astype(np.float32) / 255.0
            else:
                diff = np.zeros(image.shape[:2], dtype=np.float32)
                if classifier_flags_defect or detector_flags_defect:
                    # Circular activation at image center of mass
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
                    diff = (np.abs(gray.astype(float) - 160) / 100.0).clip(0, 1).astype(np.float32)
            heatmap = diff

        # Binary thresholding & morphological noise cleanup
        binary_raw = (heatmap >= 0.35).astype(np.uint8) * 255
        cleaned_mask = self.apply_morphological_filtering(binary_raw, kernel_size=5)

        # Extract verified geometric regions
        regions = extract_defect_regions(
            cleaned_mask,
            threshold=0.5,
            min_area_px=self.min_defect_area_px,
            mm_per_pixel=mm_per_pixel
        )

        # Step 5: Borderline & Decision Logic
        is_borderline = False
        decision_reason = "Clear unanimous consensus"
        final_decision = "PASS"
        final_defect_type = "normal"

        # Check for borderline confidence
        conf_margin = abs(clf_res.confidence - self.classifier_confidence_threshold)
        if conf_margin < self.borderline_margin and clf_res.predicted_class != "normal":
            is_borderline = True
            decision_reason = f"Borderline classifier confidence ({clf_res.confidence:.2%})"

        # Check for model disagreement
        if not dual_agreement:
            is_borderline = True
            decision_reason = (
                f"Model Disagreement: AnomalyDetector={anom_res.label} (score={anom_res.anomaly_score:.4f}), "
                f"Classifier={clf_res.predicted_class} (conf={clf_res.confidence:.2%})"
            )

        # Check for TTA disagreement (split vote)
        if tta_vote_counts.get(consensus_class, 0) < 2:
            is_borderline = True
            decision_reason = f"TTA Ensemble Voting Inconsistency: {tta_vote_counts}"

        # Final Decision Resolution
        if is_borderline:
            final_decision = "REVIEW_REQUIRED"
            final_defect_type = clf_res.predicted_class if classifier_flags_defect else "uncertain_anomaly"
            self.log_borderline_case(BorderlineLogEntry(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                sample_id=sample_id,
                status="QUARANTINED_FOR_REVIEW",
                final_decision=final_defect_type,
                dual_agreement=dual_agreement,
                anomaly_score=anom_res.anomaly_score,
                anomaly_threshold=self.anomaly_threshold,
                classifier_class=clf_res.predicted_class,
                classifier_confidence=clf_res.confidence,
                tta_votes=tta_vote_counts,
                reason=decision_reason
            ))
        elif detector_flags_defect and classifier_flags_defect and len(regions) > 0:
            final_decision = "DEFECTIVE"
            final_defect_type = consensus_class
        else:
            final_decision = "PASS"
            final_defect_type = "normal"
            regions = []  # Clear regions on verified normal part

        overall_conf = (clf_res.confidence + (1.0 if final_decision == "PASS" else anom_res.confidence)) / 2.0

        # Step 6: Generate Overlay Image
        annotated = overlay_localization_result(
            image=image,
            heatmap=heatmap if final_decision != "PASS" else None,
            regions=regions,
            defect_label=final_defect_type if final_decision != "PASS" else "normal",
            confidence=overall_conf
        )

        return RefinedInspectionResult(
            decision=final_decision,
            defect_type=final_defect_type,
            overall_confidence=round(overall_conf, 4),
            is_borderline=is_borderline,
            dual_model_agreed=dual_agreement,
            anomaly_result=anom_res,
            classifier_result=clf_res,
            tta_predictions=tta_results,
            cleaned_regions=regions,
            annotated_image=annotated
        )


if __name__ == "__main__":
    print("Testing Refinement & False Positive Reduction Engine...")
    anom_det = AnomalyDetector(approach="autoencoder")
    clf = DefectClassifier()
    engine = RefinementEngine(anom_det, clf)

    test_sample = np.full((256, 256, 3), 155, dtype=np.uint8)
    cv2.line(test_sample, (40, 40), (120, 180), (30, 30, 30), 2)

    result = engine.inspect(test_sample, sample_id="TEST_CRACK_001")
    print(f"\n[+] Inspection Result: {result.decision} (Defect Type: {result.defect_type})")
    print(f"    Confidence: {result.overall_confidence:.2%} | Borderline Flag: {result.is_borderline}")
    print(f"    Dual Model Consensus: {result.dual_model_agreed}")
    print(f"    Cleaned Defect Regions: {len(result.cleaned_regions)}")
