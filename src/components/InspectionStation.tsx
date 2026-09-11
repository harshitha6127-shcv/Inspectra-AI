import React, { useState, useMemo } from "react";
import { PartSample, InspectionResultData, DefectCategory, InspectionDecision } from "../types/inspection";
import { SAMPLE_PARTS } from "../data/sampleParts";
import { InspectionCanvas } from "./InspectionCanvas";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sliders,
  Eye,
  Camera,
  Layers,
  Cpu,
  RefreshCw,
  Ruler,
  Filter,
  ShieldCheck,
  Zap
} from "lucide-react";

export const InspectionStation: React.FC = () => {
  const [selectedSampleId, setSelectedSampleId] = useState<string>(SAMPLE_PARTS[1].id);
  const [activeView, setActiveView] = useState<
    "original" | "preprocessed" | "autoencoder_diff" | "gradcam" | "contours" | "final_hud"
  >("final_hud");

  // Tunable inspection parameters
  const [claheClip, setClaheClip] = useState<number>(2.2);
  const [kSigma, setKSigma] = useState<number>(3.0);
  const [clfThreshold, setClfThreshold] = useState<number>(0.70);
  const [useMorphFilter, setUseMorphFilter] = useState<boolean>(true);
  const [useTTA, setUseTTA] = useState<boolean>(true);
  const [mmPerPx, setMmPerPx] = useState<number>(0.12);
  const [heatmapOpacity, setHeatmapOpacity] = useState<number>(0.55);

  // Selected sample
  const sample = useMemo(() => {
    return SAMPLE_PARTS.find((p) => p.id === selectedSampleId) || SAMPLE_PARTS[0];
  }, [selectedSampleId]);

  // Compute live inspection results based on sample & tunable parameters
  const inspection = useMemo<InspectionResultData>(() => {
    const isActuallyNormal = sample.groundTruth === "normal";
    const p = sample.defectParams;

    // Simulated reconstruction error: baseline normal has 0.012 ± 0.005, defects have 0.045 to 0.120
    const baseAnomalyScore = isActuallyNormal ? 0.014 : 0.038 + p.severity * 0.065;
    const dynamicThreshold = 0.015 + kSigma * 0.007; // ~0.036 at k=3.0
    const anomalyDetected = baseAnomalyScore >= dynamicThreshold;

    // Classifier probabilities
    const probs: Record<DefectCategory, number> = {
      normal: 0.02,
      crack: 0.01,
      scratch: 0.01,
      dent: 0.01,
      stain: 0.01,
      discoloration: 0.01,
      dimensional_irregularity: 0.01
    };

    if (isActuallyNormal) {
      probs.normal = 0.94;
    } else {
      const topProb = Math.min(0.98, Math.max(0.48, p.severity * 0.92));
      probs[p.type] = topProb;
      probs.normal = Math.max(0.01, 1.0 - topProb - 0.06);
    }

    const detectedType = (Object.keys(probs) as DefectCategory[]).reduce((a, b) =>
      probs[a] > probs[b] ? a : b
    );

    const clfConfidence = probs[detectedType];
    const classifierFlagsDefect = detectedType !== "normal" && clfConfidence >= clfThreshold;

    // Dual Consensus check
    const dualModelAgreed = anomalyDetected === classifierFlagsDefect;

    // TTA votes
    const ttaVotes = [
      { viewName: "Original (0°)", predictedClass: detectedType, confidence: clfConfidence, anomalyScore: baseAnomalyScore },
      {
        viewName: "H-Flip (Mirror)",
        predictedClass: detectedType,
        confidence: Math.max(0.4, clfConfidence - 0.02),
        anomalyScore: baseAnomalyScore * 0.98
      },
      {
        viewName: "Rotated (+10°)",
        predictedClass: isActuallyNormal ? "normal" : clfConfidence > 0.65 ? detectedType : "normal",
        confidence: Math.max(0.45, clfConfidence - 0.05),
        anomalyScore: baseAnomalyScore * 1.03
      }
    ];

    // Borderline evaluation
    let isBorderline = false;
    let reason = "High-confidence consensus";

    if (sample.id === "SAMPLE-08-BORDERLINE" || !dualModelAgreed) {
      isBorderline = true;
      reason = !dualModelAgreed
        ? `Model disagreement (Detector=${anomalyDetected ? "Defect" : "Normal"}, Classifier=${detectedType})`
        : "Low classifier confidence margin";
    }

    // Final decision
    let decision: InspectionDecision = "PASS";
    if (isBorderline) {
      decision = "REVIEW_REQUIRED";
    } else if (anomalyDetected && classifierFlagsDefect) {
      decision = "DEFECTIVE";
    } else {
      decision = "PASS";
    }

    // Defect regions
    const regions = [];
    if (decision !== "PASS") {
      const areaPx = Math.round(
        p.type === "crack" ? 180 * p.severity : p.type === "dent" ? 490 : p.type === "scratch" ? 220 : 340
      );
      regions.push({
        id: 1,
        x: Math.max(10, p.cx - 25),
        y: Math.max(10, p.cy - 25),
        width: 55,
        height: 55,
        areaPx: areaPx,
        areaMm2: Number((areaPx * mmPerPx * mmPerPx).toFixed(2)),
        aspectRatio: 1.0,
        confidence: clfConfidence
      });
    }

    // Prompt 9: Severity calculation
    const typeWeights: Record<DefectCategory, number> = {
      crack: 1.00,
      dimensional_irregularity: 0.90,
      dent: 0.80,
      scratch: 0.55,
      stain: 0.35,
      discoloration: 0.30,
      normal: 0.00
    };

    let severityScore = 0.0;
    let severityCategory: "Minor" | "Major" | "Critical" | "None" = "None";
    let recommendedAction = "Pass to downstream line";
    let severityColor = "#10b981";

    if (decision !== "PASS" && detectedType !== "normal") {
      const typeW = typeWeights[detectedType] || 0.5;
      const totalDefectPx = regions.reduce((acc, r) => acc + r.areaPx, 0);
      const areaRatio = Math.min(1.0, (totalDefectPx / 65536.0) * 18.0);
      const rawScore = (0.45 * typeW + 0.35 * areaRatio + 0.20 * clfConfidence) * 100.0;
      severityScore = Math.max(0.0, Math.min(100.0, Math.round(rawScore * 10) / 10));

      if (severityScore < 30.0) {
        severityCategory = "Minor";
        recommendedAction = "Log only";
        severityColor = "#22c55e";
      } else if (severityScore <= 70.0) {
        severityCategory = "Major";
        recommendedAction = "Flag for review";
        severityColor = "#f59e0b";
      } else {
        severityCategory = "Critical";
        recommendedAction = "Reject immediately";
        severityColor = "#ef4444";
      }
    }

    return {
      decision,
      detectedType: decision === "PASS" ? "normal" : detectedType,
      overallConfidence: decision === "PASS" ? probs.normal : clfConfidence,
      anomalyScore: Number(baseAnomalyScore.toFixed(4)),
      anomalyThreshold: Number(dynamicThreshold.toFixed(4)),
      classifierProbabilities: probs,
      dualModelAgreed,
      isBorderline,
      borderlineReason: reason,
      regions,
      ttaVotes,
      processingTimeMs: 18.4,
      severityScore,
      severityCategory,
      recommendedAction,
      severityColor
    };
  }, [sample, kSigma, clfThreshold, mmPerPx]);

  return (
    <div className="space-y-6">
      {/* Sample Carousel Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 backdrop-blur shadow-sm">
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-2">
            <Camera className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Inspection Target Part
            </span>
          </div>
          <span className="text-xs text-slate-400">
            Selected: <strong className="text-white">{sample.name}</strong> ({sample.material})
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {SAMPLE_PARTS.map((p) => {
            const isSelected = p.id === sample.id;
            const isNorm = p.groundTruth === "normal";
            return (
              <button
                key={p.id}
                onClick={() => setSelectedSampleId(p.id)}
                className={`flex flex-col text-left p-2 rounded-lg border text-xs transition-all ${
                  isSelected
                    ? "bg-slate-800 border-emerald-500/80 text-white shadow-md ring-1 ring-emerald-500/40"
                    : "bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <span
                    className={`inline-block w-2 h-2 rounded-full ${
                      isNorm ? "bg-emerald-400" : p.id.includes("BORDER") ? "bg-amber-400" : "bg-rose-400"
                    }`}
                  />
                  <span className="text-[10px] font-mono text-slate-400">{p.id.split("-")[1]}</span>
                </div>
                <div className="font-medium truncate">{p.groundTruth.replace("_", " ")}</div>
                <div className="text-[10px] text-slate-400 truncate">{p.material.split(" ")[0]}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Inspection Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Visual Canvas & View Selector */}
        <div className="lg:col-span-6 space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
            {/* View Mode Tabs */}
            <div className="flex flex-wrap gap-1.5 mb-3 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
              {[
                { id: "final_hud", label: "Final HUD Overlay" },
                { id: "original", label: "Raw Input" },
                { id: "preprocessed", label: "CLAHE (LAB)" },
                { id: "autoencoder_diff", label: "Autoencoder Diff" },
                { id: "gradcam", label: "Grad-CAM Heatmap" },
                { id: "contours", label: "Contour Regions" }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveView(tab.id as any)}
                  className={`px-2.5 py-1 text-xs font-medium rounded transition-colors ${
                    activeView === tab.id
                      ? "bg-emerald-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Canvas Display */}
            <div className="flex justify-center p-2">
              <InspectionCanvas
                sample={sample}
                inspection={inspection}
                activeView={activeView}
                claheStrength={claheClip}
                showBoundingBoxes={activeView === "final_hud" || activeView === "contours"}
                heatmapOpacity={heatmapOpacity}
                mmPerPixel={mmPerPx}
              />
            </div>

            {/* Canvas Meta Info */}
            <div className="mt-3 pt-3 border-t border-slate-800/80 grid grid-cols-3 text-center text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Illumination</span>
                <span className="text-slate-200 font-medium">{sample.lightingCondition}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Substrate</span>
                <span className="text-slate-200 font-medium">{sample.material}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Latency</span>
                <span className="text-emerald-400 font-mono font-semibold">{inspection.processingTimeMs} ms</span>
              </div>
            </div>
          </div>

          {/* Interactive Inspection Tuning Controls */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
                  Pipeline Sensitivity Tuning
                </span>
              </div>
              <button
                onClick={() => {
                  setClaheClip(2.2);
                  setKSigma(3.0);
                  setClfThreshold(0.70);
                  setMmPerPx(0.12);
                }}
                className="text-[11px] text-slate-400 hover:text-emerald-400 flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Reset Defaults
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {/* CLAHE Clip Limit */}
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>CLAHE Clip Limit (L-Channel)</span>
                  <span className="font-mono text-emerald-400">{claheClip.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="5.0"
                  step="0.2"
                  value={claheClip}
                  onChange={(e) => setClaheClip(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 bg-slate-800 h-1.5 rounded cursor-pointer"
                />
              </div>

              {/* Anomaly Threshold k*sigma */}
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Anomaly Threshold (mean + k·σ)</span>
                  <span className="font-mono text-emerald-400">{kSigma.toFixed(1)}σ</span>
                </div>
                <input
                  type="range"
                  min="1.5"
                  max="4.5"
                  step="0.1"
                  value={kSigma}
                  onChange={(e) => setKSigma(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 bg-slate-800 h-1.5 rounded cursor-pointer"
                />
              </div>

              {/* Classifier Confidence Threshold */}
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Classifier Acceptance Threshold</span>
                  <span className="font-mono text-emerald-400">{Math.round(clfThreshold * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0.50"
                  max="0.95"
                  step="0.05"
                  value={clfThreshold}
                  onChange={(e) => setClfThreshold(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 bg-slate-800 h-1.5 rounded cursor-pointer"
                />
              </div>

              {/* Pixel-to-mm scale */}
              <div>
                <div className="flex justify-between text-slate-300 mb-1">
                  <span>Optics Scale Calibration</span>
                  <span className="font-mono text-emerald-400">{mmPerPx.toFixed(2)} mm/px</span>
                </div>
                <input
                  type="range"
                  min="0.05"
                  max="0.30"
                  step="0.01"
                  value={mmPerPx}
                  onChange={(e) => setMmPerPx(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 bg-slate-800 h-1.5 rounded cursor-pointer"
                />
              </div>
            </div>

            {/* Toggles */}
            <div className="flex flex-wrap gap-4 pt-1">
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useMorphFilter}
                  onChange={(e) => setUseMorphFilter(e.target.checked)}
                  className="accent-emerald-500 rounded"
                />
                <span>Morphological Noise Rejection</span>
              </label>

              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useTTA}
                  onChange={(e) => setUseTTA(e.target.checked)}
                  className="accent-emerald-500 rounded"
                />
                <span>Test-Time Augmentation (TTA Ensemble)</span>
              </label>
            </div>
          </div>
        </div>

        {/* Right Column: Decisions, Probabilities, Localization & TTA */}
        <div className="lg:col-span-6 space-y-4">
          {/* Production Decision Card */}
          <div
            className={`border rounded-xl p-4 shadow-sm ${
              inspection.decision === "PASS"
                ? "bg-emerald-950/40 border-emerald-500/40"
                : inspection.decision === "REVIEW_REQUIRED"
                ? "bg-amber-950/40 border-amber-500/40"
                : "bg-rose-950/40 border-rose-500/40"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {inspection.decision === "PASS" ? (
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
                    <CheckCircle2 className="w-6 h-6" />
                  </div>
                ) : inspection.decision === "REVIEW_REQUIRED" ? (
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
                    <AlertTriangle className="w-6 h-6" />
                  </div>
                ) : (
                  <div className="w-10 h-10 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
                    <XCircle className="w-6 h-6" />
                  </div>
                )}
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Inspection Station Verdict
                  </div>
                  <div className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                    {inspection.decision === "PASS"
                      ? "PASS — CONFORMING"
                      : inspection.decision === "REVIEW_REQUIRED"
                      ? "QUARANTINE — QA REVIEW"
                      : `REJECT — DEFECTIVE`}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-2xl font-black font-mono text-white">
                  {(inspection.overallConfidence * 100).toFixed(1)}%
                </div>
                <div className="text-[11px] text-slate-400">Confidence</div>
              </div>
            </div>

            {/* Reasoning Tag */}
            <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs">
              <span className="text-slate-300">
                Classification:{" "}
                <strong className="text-white capitalize">
                  {inspection.detectedType.replace("_", " ")}
                </strong>
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                  inspection.dualModelAgreed
                    ? "bg-emerald-900/60 text-emerald-300 border border-emerald-700/50"
                    : "bg-amber-900/60 text-amber-300 border border-amber-700/50"
                }`}
              >
                {inspection.dualModelAgreed ? "Dual Consensus Verified" : "Model Discrepancy Flagged"}
              </span>
            </div>
          </div>

          {/* Prompt 9: Severity Scoring & Factory Disposition */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200 uppercase tracking-wide">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Defect Severity Assessment (Prompt 9)</span>
              </div>
              <span
                className="px-2 py-0.5 rounded text-[11px] font-bold"
                style={{
                  backgroundColor: `${inspection.severityColor}25`,
                  color: inspection.severityColor,
                  border: `1px solid ${inspection.severityColor}50`
                }}
              >
                {inspection.severityCategory.toUpperCase()} SEVERITY
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-950/80 p-2.5 rounded border border-slate-800/80">
                <div className="text-slate-400 text-[11px] mb-0.5">Composite Severity Score:</div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-bold font-mono" style={{ color: inspection.severityColor }}>
                    {inspection.severityScore}
                  </span>
                  <span className="text-slate-500 font-mono text-xs">/ 100</span>
                </div>
                {/* 3-Tier color progress bar */}
                <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-1.5">
                  <div
                    className="h-full transition-all duration-300 rounded-full"
                    style={{
                      width: `${inspection.severityScore}%`,
                      backgroundColor: inspection.severityColor
                    }}
                  />
                </div>
              </div>

              <div className="bg-slate-950/80 p-2.5 rounded border border-slate-800/80">
                <div className="text-slate-400 text-[11px] mb-0.5">Recommended Disposition:</div>
                <div className="text-sm font-semibold text-cyan-300 mt-1">
                  {inspection.recommendedAction}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">
                  {inspection.severityCategory === "Critical"
                    ? "Immediate quarantine & line alert"
                    : inspection.severityCategory === "Major"
                    ? "Manual engineer inspection queue"
                    : "Logged in manufacturing telemetry"}
                </div>
              </div>
            </div>
          </div>

          {/* Stage 1: Anomaly Detector vs Stage 2: Classifier */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
                Stage 1 & Stage 2 Model Outputs
              </span>
              <span className="text-[11px] font-mono text-slate-400">MSE + SSIM Score</span>
            </div>

            {/* Anomaly Gauge Bar */}
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300">Reconstruction Error:</span>
                <span className="font-mono text-white">
                  {inspection.anomalyScore.toFixed(4)} / Threshold {inspection.anomalyThreshold.toFixed(4)}
                </span>
              </div>
              <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-800 relative">
                <div
                  className={`h-full transition-all duration-300 ${
                    inspection.anomalyScore >= inspection.anomalyThreshold
                      ? "bg-rose-500"
                      : "bg-emerald-500"
                  }`}
                  style={{ width: `${Math.min(100, (inspection.anomalyScore / 0.10) * 100)}%` }}
                />
                {/* Threshold Marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-yellow-400 z-10"
                  style={{ left: `${Math.min(100, (inspection.anomalyThreshold / 0.10) * 100)}%` }}
                />
              </div>
            </div>

            {/* Softmax Probability Bars */}
            <div className="space-y-1.5 pt-1">
              <div className="text-xs text-slate-400 mb-1">Multi-Class Softmax Distribution:</div>
              {(Object.entries(inspection.classifierProbabilities) as [DefectCategory, number][]).map(
                ([cat, prob]) => {
                  const isTop = cat === inspection.detectedType;
                  return (
                    <div key={cat} className="flex items-center text-xs gap-2">
                      <span className={`w-36 capitalize truncate ${isTop ? "font-semibold text-white" : "text-slate-400"}`}>
                        {cat.replace("_", " ")}
                      </span>
                      <div className="flex-1 bg-slate-950 h-2 rounded overflow-hidden">
                        <div
                          className={`h-full ${
                            cat === "normal"
                              ? "bg-emerald-500"
                              : isTop
                              ? "bg-rose-500"
                              : "bg-slate-700"
                          }`}
                          style={{ width: `${Math.round(prob * 100)}%` }}
                        />
                      </div>
                      <span className="w-12 text-right font-mono text-slate-300 text-[11px]">
                        {(prob * 100).toFixed(0)}%
                      </span>
                    </div>
                  );
                }
              )}
            </div>
          </div>

          {/* Stage 3: Localization Regions & Stage 4: TTA Ensemble */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Defect Region Geometry */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
              <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-200 uppercase tracking-wide">
                <Ruler className="w-3.5 h-3.5 text-emerald-400" />
                <span>Defect Metrology</span>
              </div>
              {inspection.regions.length > 0 ? (
                <div className="space-y-2 text-xs">
                  {inspection.regions.map((r) => (
                    <div key={r.id} className="bg-slate-950/80 p-2 rounded border border-slate-800/80 space-y-1">
                      <div className="flex justify-between font-mono text-slate-300">
                        <span>Area (mm²):</span>
                        <strong className="text-rose-400 font-bold">{r.areaMm2} mm²</strong>
                      </div>
                      <div className="flex justify-between font-mono text-slate-400 text-[11px]">
                        <span>Area (pixels):</span>
                        <span>{r.areaPx} px²</span>
                      </div>
                      <div className="flex justify-between font-mono text-slate-400 text-[11px]">
                        <span>BBox (x, y, w, h):</span>
                        <span>{r.x}, {r.y}, {r.width}×{r.height}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-400 italic p-3 text-center bg-slate-950/40 rounded border border-slate-800/40">
                  No defective regions detected above minimum threshold.
                </div>
              )}
            </div>

            {/* TTA Voting Matrix */}
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
              <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-slate-200 uppercase tracking-wide">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>TTA Ensemble Voting</span>
              </div>
              <div className="space-y-1.5 text-xs">
                {inspection.ttaVotes.map((v, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-950/80 px-2 py-1.5 rounded border border-slate-800/80">
                    <span className="text-slate-300 text-[11px] truncate">{v.viewName}</span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                          v.predictedClass === "normal"
                            ? "bg-emerald-950 text-emerald-300"
                            : "bg-rose-950 text-rose-300"
                        }`}
                      >
                        {v.predictedClass}
                      </span>
                      <span className="font-mono text-slate-400 text-[11px]">
                        {(v.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
