"""
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

import os
import sys
import argparse
import time
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import cv2

# Ensure src/ is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from dataset import DEFECT_CLASSES, create_base_texture, inject_crack, inject_scratch, inject_dent, inject_stain, inject_discoloration, inject_dimensional_irregularity
from pipeline import get_pipeline, run_inspection


def compute_mask_iou(pred_mask: np.ndarray, gt_mask: np.ndarray) -> float:
    """
    Computes Intersection over Union (IoU) between predicted and ground-truth binary masks.
    """
    pred_bin = (pred_mask > 0).astype(bool)
    gt_bin = (gt_mask > 0).astype(bool)

    intersection = np.logical_and(pred_bin, gt_bin).sum()
    union = np.logical_or(pred_bin, gt_bin).sum()

    if union == 0:
        # If both are empty (i.e. normal sample), perfect match = 1.0
        return 1.0 if not pred_bin.any() and not gt_bin.any() else 0.0

    return float(intersection) / float(union)


def compute_bbox_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """
    Computes IoU between two bounding boxes (x, y, w, h).
    """
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interWidth = max(0, xB - xA)
    interHeight = max(0, yB - yA)
    interArea = interWidth * interHeight

    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    unionArea = float(boxAArea + boxBArea - interArea)

    if unionArea == 0:
        return 0.0
    return interArea / unionArea


def calculate_binary_metrics(y_true_binary: List[int], y_pred_binary: List[int], y_scores: List[float]) -> Dict[str, float]:
    """
    Calculates Accuracy, Precision, Recall, F1, and ROC-AUC for binary anomaly classification.
    """
    try:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        acc = accuracy_score(y_true_binary, y_pred_binary)
        prec = precision_score(y_true_binary, y_pred_binary, zero_division=0)
        rec = recall_score(y_true_binary, y_pred_binary, zero_division=0)
        f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
        try:
            auc = roc_auc_score(y_true_binary, y_scores)
        except Exception:
            auc = 0.5
    except ImportError:
        # Pure NumPy fallback
        yt = np.array(y_true_binary)
        yp = np.array(y_pred_binary)
        tp = np.sum((yt == 1) & (yp == 1))
        tn = np.sum((yt == 0) & (yp == 0))
        fp = np.sum((yt == 0) & (yp == 1))
        fn = np.sum((yt == 1) & (yp == 0))
        total = len(yt)
        acc = float((tp + tn) / max(1, total))
        prec = float(tp / max(1, (tp + fp)))
        rec = float(tp / max(1, (tp + fn)))
        f1 = float(2 * prec * rec / max(1e-8, (prec + rec)))
        auc = 0.5

    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "roc_auc": float(auc)
    }


def calculate_multiclass_metrics(y_true_classes: List[str], y_pred_classes: List[str], classes: List[str]) -> Tuple[Dict[str, Dict[str, float]], float, float, np.ndarray]:
    """
    Computes per-class Precision, Recall, F1, Macro F1, Weighted F1, and Confusion Matrix.
    """
    try:
        from sklearn.metrics import classification_report, confusion_matrix, f1_score
        report_dict = classification_report(y_true_classes, y_pred_classes, labels=classes, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_true_classes, y_pred_classes, labels=classes)
        macro_f1 = f1_score(y_true_classes, y_pred_classes, labels=classes, average="macro", zero_division=0)
        weighted_f1 = f1_score(y_true_classes, y_pred_classes, labels=classes, average="weighted", zero_division=0)
        
        per_class = {}
        for c in classes:
            if c in report_dict:
                per_class[c] = {
                    "precision": report_dict[c]["precision"],
                    "recall": report_dict[c]["recall"],
                    "f1": report_dict[c]["f1-score"],
                    "support": report_dict[c]["support"]
                }
            else:
                per_class[c] = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
        return per_class, float(macro_f1), float(weighted_f1), cm
    except ImportError:
        # Fallback implementation
        cm = np.zeros((len(classes), len(classes)), dtype=int)
        class_to_idx = {c: i for i, c in enumerate(classes)}
        for yt, yp in zip(y_true_classes, y_pred_classes):
            if yt in class_to_idx and yp in class_to_idx:
                cm[class_to_idx[yt], class_to_idx[yp]] += 1

        per_class = {}
        f1_list = []
        for i, c in enumerate(classes):
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            prec = tp / max(1, tp + fp)
            rec = tp / max(1, tp + fn)
            f1 = 2 * prec * rec / max(1e-8, prec + rec)
            support = int(cm[i, :].sum())
            per_class[c] = {"precision": float(prec), "recall": float(rec), "f1": float(f1), "support": support}
            f1_list.append(f1)

        macro_f1 = float(np.mean(f1_list))
        weighted_f1 = macro_f1
        return per_class, macro_f1, weighted_f1, cm


def plot_and_save_curves(
    y_true_binary: List[int],
    y_scores: List[float],
    y_true_classes: List[str],
    y_pred_classes: List[str],
    classes: List[str],
    cm: np.ndarray,
    output_dir: str = "outputs"
):
    """
    Plots and saves:
    1. ROC Curve
    2. Precision-Recall Curve
    3. Normalized Confusion Matrix
    """
    os.makedirs(output_dir, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import roc_curve, precision_recall_curve, auc

        # 1. Plot ROC Curve
        fpr, tpr, _ = roc_curve(y_true_binary, y_scores)
        roc_auc_val = auc(fpr, tpr)

        plt.figure(figsize=(6, 5))
        plt.plot(fpr, tpr, color="#2563eb", lw=2, label=f"ROC Curve (AUC = {roc_auc_val:.3f})")
        plt.plot([0, 1], [0, 1], color="#94a3b8", lw=1.5, linestyle="--", label="Random Chance")
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate (1 - Specificity)")
        plt.ylabel("True Positive Rate (Sensitivity / Recall)")
        plt.title("Defect Detection — Receiver Operating Characteristic (ROC)")
        plt.legend(loc="lower right")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "roc_curve.png"), dpi=150)
        plt.close()

        # 2. Plot Precision-Recall Curve
        prec_curve, rec_curve, _ = precision_recall_curve(y_true_binary, y_scores)
        pr_auc_val = auc(rec_curve, prec_curve)

        plt.figure(figsize=(6, 5))
        plt.plot(rec_curve, prec_curve, color="#16a34a", lw=2, label=f"PR Curve (AUC = {pr_auc_val:.3f})")
        plt.xlabel("Recall")
        plt.ylabel("Precision")
        plt.title("Defect Detection — Precision-Recall Curve")
        plt.legend(loc="lower left")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "precision_recall_curve.png"), dpi=150)
        plt.close()

        # 3. Plot Normalized Confusion Matrix
        cm_normalized = cm.astype("float") / np.maximum(1, cm.sum(axis=1)[:, np.newaxis])
        plt.figure(figsize=(8, 7))
        plt.imshow(cm_normalized, interpolation="nearest", cmap=plt.cm.Blues)
        plt.title("Multi-Class Defect Classifier — Normalized Confusion Matrix")
        plt.colorbar()
        tick_marks = np.arange(len(classes))
        display_names = [c.replace("_", " ") for c in classes]
        plt.xticks(tick_marks, display_names, rotation=45, ha="right", fontsize=9)
        plt.yticks(tick_marks, display_names, fontsize=9)

        # Annotate text counts and percentages in each cell
        thresh = cm_normalized.max() / 2.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                raw_count = cm[i, j]
                pct = cm_normalized[i, j] * 100.0
                text = f"{raw_count}\n({pct:.0f}%)" if raw_count > 0 else "0"
                plt.text(
                    j, i, text,
                    horizontalalignment="center",
                    verticalalignment="center",
                    color="white" if cm_normalized[i, j] > thresh else "black",
                    fontsize=8
                )

        plt.ylabel("True Ground-Truth Class")
        plt.xlabel("Predicted Class")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "confusion_matrix.png"), dpi=150)
        plt.close()

    except Exception as e:
        print(f"[!] Warning: Could not generate plots with matplotlib ({e}).")


def run_evaluation(
    samples_per_class: int = 15,
    output_dir: str = "outputs"
) -> Dict[str, Any]:
    """
    Executes full Prompt 6 benchmark evaluation across all 7 defect classes.
    """
    print("=" * 70)
    print("  RUNNING QUANTITATIVE BENCHMARK EVALUATION (PROMPT 6)")
    print("=" * 70)

    os.makedirs(output_dir, exist_ok=True)
    pipeline = get_pipeline()

    # Generate synthetic benchmark evaluation set with ground truth masks
    generators = {
        "normal": lambda base: (base, np.zeros(base.shape[:2], dtype=np.uint8)),
        "crack": inject_crack,
        "scratch": inject_scratch,
        "dent": inject_dent,
        "stain": inject_stain,
        "discoloration": inject_discoloration,
        "dimensional_irregularity": inject_dimensional_irregularity
    }

    y_true_binary: List[int] = []
    y_pred_binary: List[int] = []
    y_anomaly_scores: List[float] = []

    y_true_classes: List[str] = []
    y_pred_classes: List[str] = []

    iou_scores: List[float] = []
    defective_iou_scores: List[float] = []

    print(f"[*] Synthesizing and testing {samples_per_class * len(DEFECT_CLASSES)} evaluation samples...")
    start_time = time.time()

    for defect_class in DEFECT_CLASSES:
        gen_fn = generators[defect_class]
        is_true_defective = (defect_class != "normal")

        for s_idx in range(samples_per_class):
            base_tex = create_base_texture(256, 256, texture_type="brushed_metal")
            img, gt_mask = gen_fn(base_tex)

            # Inspect
            sample_id = f"EVAL_{defect_class}_{s_idx:03d}"
            insp = pipeline.inspect_image(img, sample_id=sample_id)

            pred_defective = (insp.decision != "PASS")
            anomaly_score = insp.anomaly_score
            pred_class = insp.defect_type if pred_defective else "normal"

            # 1. Binary metrics records
            y_true_binary.append(1 if is_true_defective else 0)
            y_pred_binary.append(1 if pred_defective else 0)
            y_anomaly_scores.append(anomaly_score)

            # 2. Multi-class metrics records
            y_true_classes.append(defect_class)
            y_pred_classes.append(pred_class)

            # 3. Mask IoU calculation
            pred_mask = np.zeros((256, 256), dtype=np.uint8)
            if pred_defective and insp.cleaned_regions:
                for r in insp.cleaned_regions:
                    cv2.rectangle(pred_mask, (r.x, r.y), (r.x + r.width, r.y + r.height), 255, -1)

            iou = compute_mask_iou(pred_mask, gt_mask)
            iou_scores.append(iou)
            if is_true_defective:
                defective_iou_scores.append(iou)

    eval_time = time.time() - start_time

    # Calculate metrics
    bin_metrics = calculate_binary_metrics(y_true_binary, y_pred_binary, y_anomaly_scores)
    per_class, macro_f1, weighted_f1, cm = calculate_multiclass_metrics(y_true_classes, y_pred_classes, DEFECT_CLASSES)

    mean_iou_all = float(np.mean(iou_scores))
    mean_iou_defective = float(np.mean(defective_iou_scores)) if defective_iou_scores else 0.0

    # Save plots
    plot_and_save_curves(
        y_true_binary, y_anomaly_scores,
        y_true_classes, y_pred_classes,
        DEFECT_CLASSES, cm, output_dir=output_dir
    )

    # 4. Generate Single Comprehensive Text Report
    report_lines = [
        "================================================================================",
        "          VISION-BASED DEFECT DETECTION — MODEL EVALUATION REPORT",
        "================================================================================",
        f"Evaluation Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Samples Evaluated: {len(y_true_binary)} ({samples_per_class} per class across 7 categories)",
        f"Total Evaluation Runtime: {eval_time:.2f}s ({eval_time / len(y_true_binary) * 1000.0:.1f} ms/sample)",
        "",
        "--------------------------------------------------------------------------------",
        "  1. STAGE 1: DEFECTIVE VS. NORMAL ANOMALY DETECTION METRICS",
        "--------------------------------------------------------------------------------",
        f"  - Accuracy:         {bin_metrics['accuracy']:.4f}  ({bin_metrics['accuracy']*100:.1f}%)",
        f"  - Precision:        {bin_metrics['precision']:.4f}  ({bin_metrics['precision']*100:.1f}%)",
        f"  - Recall:           {bin_metrics['recall']:.4f}  ({bin_metrics['recall']*100:.1f}%)",
        f"  - F1-Score:         {bin_metrics['f1_score']:.4f}",
        f"  - ROC-AUC:          {bin_metrics['roc_auc']:.4f}",
        "",
        "--------------------------------------------------------------------------------",
        "  2. STAGE 2: MULTI-CLASS DEFECT CLASSIFICATION METRICS",
        "--------------------------------------------------------------------------------",
        f"  {'Defect Class':<28} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}",
        "  " + "-" * 74
    ]

    for c in DEFECT_CLASSES:
        m = per_class.get(c, {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0})
        name = c.replace("_", " ").title()
        report_lines.append(f"  {name:<28} | {m['precision']:<10.3f} | {m['recall']:<10.3f} | {m['f1']:<10.3f} | {m['support']:<8}")

    report_lines.extend([
        "  " + "-" * 74,
        f"  Macro-Averaged F1-Score:    {macro_f1:.4f}",
        f"  Weighted-Averaged F1-Score: {weighted_f1:.4f}",
        "",
        "--------------------------------------------------------------------------------",
        "  3. STAGE 3: DEFECT LOCALIZATION ACCURACY (IoU)",
        "--------------------------------------------------------------------------------",
        f"  - Mean IoU (Defective Samples Only): {mean_iou_defective:.4f}  ({mean_iou_defective*100:.1f}%)",
        f"  - Overall Mean IoU (All Samples):   {mean_iou_all:.4f}  ({mean_iou_all*100:.1f}%)",
        "",
        "--------------------------------------------------------------------------------",
        "  4. GENERATED ARTIFACTS & VISUALIZATIONS",
        "--------------------------------------------------------------------------------",
        f"  - ROC Curve Plot:                {os.path.join(output_dir, 'roc_curve.png')}",
        f"  - Precision-Recall Curve Plot:   {os.path.join(output_dir, 'precision_recall_curve.png')}",
        f"  - Normalized Confusion Matrix:   {os.path.join(output_dir, 'confusion_matrix.png')}",
        f"  - Complete Text Audit Report:    {os.path.join(output_dir, 'evaluation_report.txt')}",
        "================================================================================"
    ])

    report_text = "\n".join(report_lines)
    report_file_path = os.path.join(output_dir, "evaluation_report.txt")
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n[+] Full evaluation report successfully saved to: {report_file_path}")

    return {
        "binary_metrics": bin_metrics,
        "per_class": per_class,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "mean_iou_defective": mean_iou_defective,
        "mean_iou_all": mean_iou_all,
        "report_path": report_file_path
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Vision-Based Defect Detection System")
    parser.add_argument("--samples", type=int, default=15, help="Number of test samples per class")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Output directory for reports and plots")
    args = parser.parse_args()

    run_evaluation(samples_per_class=args.samples, output_dir=args.output_dir)
