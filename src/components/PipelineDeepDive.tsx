import React, { useState } from "react";
import {
  Layers,
  Sparkles,
  Shield,
  Activity,
  Maximize2,
  Filter,
  BarChart2,
  Search,
  CheckCircle,
  FileCode
} from "lucide-react";

interface StageInfo {
  id: string;
  prompt: string;
  title: string;
  file: string;
  badge: string;
  description: string;
  keyComponents: string[];
  formula?: string;
  architecture: string[];
}

const STAGES: StageInfo[] = [
  {
    id: "p0",
    prompt: "Prompt 0",
    title: "Project Scaffolding & Dataset Preparation",
    file: "prepare_dataset.py / src/dataset.py",
    badge: "Foundation",
    description:
      "Dual-mode dataset preparation architecture supporting the official industrial MVTec Anomaly Detection (MVTec AD) benchmark or procedural OpenCV synthetic defect generation for 7 categories.",
    keyComponents: [
      "Directory Structure: data/raw, data/processed, src/, models/, outputs/, notebooks/",
      "MVTec AD categories: bottle, cable, capsule, carpet, grid, hazelnut, metal_nut, tile, screw, etc.",
      "OpenCV Procedural Defect Injector: cracks (branching random walk), scratches (shadow groove + specular highlight), dents (3D Gaussian illumination), stains (soft organic blobs), discoloration (HSV/LAB hue shifts), dimensional errors (perimeter chip)",
      "Pixel-level binary ground truth mask generation for every synthetic sample",
      "Tabular dataset summary report (split counts, image resolutions, class frequencies)"
    ],
    architecture: ["Raw Substrate Generator", "Defect Procedural Injection", "Ground Truth Masking", "Train / Val / Test Split"]
  },
  {
    id: "p1",
    prompt: "Prompt 1",
    title: "Preprocessing & Lighting Normalization",
    file: "src/preprocessing.py",
    badge: "OpenCV Conditioning",
    description:
      "Normalizes hostile factory lighting conditions, directional glares, sensor noise, and orientation shifts before neural network ingestion.",
    keyComponents: [
      "Aspect-Ratio Preserving Letterbox: Symmetrically pads images into 256x256 without distortion",
      "Luminance CLAHE in CIE LAB: Applies Contrast Limited Adaptive Histogram Equalization strictly to the L-channel, enhancing micro-defects without color oversaturation",
      "Edge-Preserving Bilateral Filter: Smooths sensor noise while preserving sharp boundaries of hairline fractures and scratches",
      "Background Normalization & ROI Cropping: Removes conveyor belts, brackets, and jigs using Otsu thresholding and contour bounding",
      "Albumentations Augmentation: Random rotations, flips, perspective jitter, and lighting shifts"
    ],
    formula: "LAB(L, a, b) \\rightarrow L_{CLAHE} = \\text{EqualizeTile}(L, \\text{clip}=2.0) \\rightarrow BGR",
    architecture: ["Raw Frame", "ROI Extractor", "LAB CLAHE", "Bilateral Denoise", "Letterbox Pad"]
  },
  {
    id: "p2",
    prompt: "Prompt 2",
    title: "Anomaly Detection (Defective vs Normal)",
    file: "src/anomaly_detection.py",
    badge: "Unsupervised Stage",
    description:
      "Deep Convolutional Autoencoder (CAE) trained exclusively on normal (defect-free) parts. Anomaly score derived from hybrid MSE and SSIM reconstruction error.",
    keyComponents: [
      "Convolutional Autoencoder: 4-stage encoder with LeakyReLU + BatchNorm down to 16x16 bottleneck, mirrored transpose decoder with Sigmoid output",
      "Hybrid Reconstruction Loss: 60% MSE loss + 40% (1 - SSIM) structural similarity loss",
      "Statistical Calibration: Automated threshold computation on normal validation set using μ + k·σ (default k=3.0)",
      "Alternative Transfer Learning Mode: Pretrained EfficientNet-B0 or ResNet-50 binary classifier switchable via config flag",
      "ROC Curve Optimization: Optional Youden's J-statistic maximization on labeled validation anomalies"
    ],
    formula: "\\text{Score}(x) = 0.6 \\cdot \\text{MSE}(x, \\hat{x}) + 0.4 \\cdot (1 - \\text{SSIM}(x, \\hat{x})) \\ge \\mu + k\\sigma",
    architecture: ["Input Tensor [3, 256, 256]", "CAE Encoder", "Latent Bottleneck", "CAE Decoder", "Reconstruction Loss"]
  },
  {
    id: "p3",
    prompt: "Prompt 3",
    title: "Defect Type Multi-Class Classification",
    file: "src/defect_classifier.py",
    badge: "Supervised Transfer Learning",
    description:
      "Deep Convolutional Network (EfficientNet-B0 / MobileNet-V2) classifying parts into 7 classes with Focal Loss to handle severe industrial class imbalance.",
    keyComponents: [
      "7-Class Categorization: normal, crack, scratch, dent, stain, discoloration, dimensional_irregularity",
      "Two-Phase Training: Frozen backbone head adaptation -> full fine-tuning with CosineAnnealingLR",
      "Focal Loss: FL(p_t) = -α_t(1 - p_t)^γ log(p_t) to suppress easy normal examples and prioritize hard defect boundaries",
      "Inverse Class Frequency Weights: Normalizes gradients for rare defect types",
      "Comprehensive Diagnostics: Normalized confusion matrix and per-class Precision / Recall / F1 reporting"
    ],
    formula: "FL(p_t) = -\\alpha_t (1 - p_t)^\\gamma \\log(p_t), \\quad \\gamma = 2.0",
    architecture: ["EfficientNet-B0 Backbone", "Global Avg Pooling", "Dropout (0.35)", "Dense 128 (SiLU)", "Softmax 7-Class"]
  },
  {
    id: "p4",
    prompt: "Prompt 4",
    title: "Defect Localization (Grad-CAM & Contours)",
    file: "src/localization.py",
    badge: "Spatial Metrology",
    description:
      "Generates pixel-level activation heatmaps using Grad-CAM hooks and extracts geometric bounding boxes and calibrated physical measurements via OpenCV contours.",
    keyComponents: [
      "Grad-CAM on Classifier: Computes gradients of target defect class score w.r.t. final convolutional feature activations",
      "Lightweight U-Net Alternative: Compact 4-stage encoder-decoder with skip connections for pixel-level binary segmentation",
      "OpenCV Contour Analysis: Binarizes activation map, executes cv2.findContours, and computes bounding rectangles",
      "Physical Metrology: Converts pixel area into calibrated square millimeters (mm²) using camera optics ratio",
      "Industrial HUD Overlay: Composes thermal jet colormap, bounding boxes, labels, and defect area onto inspection frame"
    ],
    formula: "L^c_{Grad-CAM} = \\text{ReLU}\\left(\\sum_k \\alpha_k^c A^k\\right), \\quad \\alpha_k^c = \\frac{1}{Z} \\sum_i \\sum_j \\frac{\\partial y^c}{\\partial A_{i,j}^k}",
    architecture: ["Feature Activation Hook", "Gradient Backprop", "Jet Colormap Blend", "Contour Extractor", "Calibrated Bounding Boxes"]
  },
  {
    id: "p5",
    prompt: "Prompt 5",
    title: "False Positive Reduction & Robustness",
    file: "src/refinement.py",
    badge: "Quality Assurance",
    description:
      "Multi-layered verification engine enforcing dual-model consensus, morphological noise cleaning, Test-Time Augmentation (TTA), and borderline quarantine logging.",
    keyComponents: [
      "Dual-Model Consensus: Both the Anomaly Detector (reconstruction error) AND Classifier must agree on defect status",
      "Morphological Filtering: Opening (erosion -> dilation) eradicates dust speckles; closing bridges micro-fractures in cracks",
      "Minimum Defect Area Threshold: Discards candidate regions smaller than 25 pixels",
      "Test-Time Augmentation (TTA): 3-view voting (Original, Horizontal Flip, +10° Rotation) to distinguish persistent physical defects from transient specular glare",
      "Borderline Quarantine Logging: Quarantines low-margin or conflicting samples into structured review queue for manual human QA"
    ],
    formula: "\\text{Defect Confirmed} \\iff (\\text{Score}_{CAE} \\ge \\tau_{anom}) \\land (P(c) \\ge \\tau_{clf}) \\land (\\text{TTA Votes} \\ge 2)",
    architecture: ["Dual Model Inferences", "TTA 3-View Voting", "Morphological Opening/Closing", "Borderline Audit Logger"]
  }
];

export const PipelineDeepDive: React.FC = () => {
  const [activeStageId, setActiveStageId] = useState<string>("p0");
  const stage = STAGES.find((s) => s.id === activeStageId) || STAGES[0];

  return (
    <div className="space-y-6">
      {/* Stage Selector Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {STAGES.map((s, idx) => {
          const isSelected = s.id === stage.id;
          return (
            <button
              key={s.id}
              onClick={() => setActiveStageId(s.id)}
              className={`p-3 rounded-xl text-left border transition-all ${
                isSelected
                  ? "bg-slate-900 border-emerald-500 shadow-md ring-1 ring-emerald-500/40 text-white"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
              }`}
            >
              <div className="text-[11px] font-mono text-emerald-400 font-semibold mb-1">
                {s.prompt}
              </div>
              <div className="font-semibold text-xs text-slate-200 truncate">{s.title.split(" ")[0]} {s.title.split(" ")[1]}</div>
              <div className="text-[10px] text-slate-400 truncate mt-0.5">{s.badge}</div>
            </button>
          );
        })}
      </div>

      {/* Selected Stage Detail Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wide">
                {stage.prompt} Specification
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800/50">
                {stage.badge}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">{stage.title}</h2>
            <div className="text-xs font-mono text-slate-400 mt-0.5">Source Module: {stage.file}</div>
          </div>
        </div>

        <p className="text-slate-300 text-sm leading-relaxed">{stage.description}</p>

        {/* Pipeline Architecture Flow */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Stage Execution Flow
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {stage.architecture.map((step, i) => (
              <React.Fragment key={i}>
                <div className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 font-medium shadow-sm">
                  {step}
                </div>
                {i < stage.architecture.length - 1 && (
                  <span className="text-emerald-500 font-mono text-xs">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Mathematical Formulation (if applicable) */}
        {stage.formula && (
          <div className="bg-slate-950/80 border border-slate-800/90 rounded-lg p-3.5">
            <div className="text-[11px] font-mono text-slate-400 mb-1">Algorithmic Formulation:</div>
            <code className="text-xs font-mono text-emerald-300 block">{stage.formula}</code>
          </div>
        )}

        {/* Key Technical Requirements Checklist */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5">
            Technical Implementation Highlights
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {stage.keyComponents.map((comp, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/60 text-xs text-slate-300"
              >
                <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <span>{comp}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
