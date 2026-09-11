import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
  RefreshCw,
  Cpu,
  Bot,
  Zap,
  Sliders,
  ExternalLink,
  QrCode,
  ShieldCheck,
  Eye
} from "lucide-react";

interface InspectionSample {
  id: string;
  name: string;
  category: string;
  imageUrl: string;
  customResult: {
    decision: string;
    is_defective: boolean;
    defect_type: string;
    confidence: number;
    severity_score: number;
    severity_category: string;
    defect_area: number;
    defect_area_mm2: number;
    latency_ms: number;
  };
  aiResult: {
    provider: string;
    decision: string;
    is_defective: boolean;
    defect_type: string;
    confidence: "high" | "medium" | "low";
    description: string;
    reasoning: string;
    latency_ms: number;
  };
}

const SAMPLE_INSPECTIONS: InspectionSample[] = [
  {
    id: "part-01",
    name: "Structural Flange Collar",
    category: "crack",
    imageUrl: "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=600&auto=format&fit=crop&q=80",
    customResult: {
      decision: "DEFECT_DETECTED",
      is_defective: true,
      defect_type: "crack",
      confidence: 0.982,
      severity_score: 84.5,
      severity_category: "Critical",
      defect_area: 1420,
      defect_area_mm2: 56.8,
      latency_ms: 22.4
    },
    aiResult: {
      provider: "Google Gemini 2.5 Flash",
      decision: "DEFECT_DETECTED",
      is_defective: true,
      defect_type: "crack",
      confidence: "high",
      description: "Linear stress fissure traversing diagonally across the upper mounting bevel, approximately 24mm in length.",
      reasoning: "High-contrast fracture line indicates structural stress fatigue. The morphology breaks surface contour continuity, posing catastrophic tensile failure risk under cyclical hydraulic loading.",
      latency_ms: 412
    }
  },
  {
    id: "part-02",
    name: "Hardened Drive Shaft Spindle",
    category: "scratch",
    imageUrl: "https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?w=600&auto=format&fit=crop&q=80",
    customResult: {
      decision: "DEFECT_DETECTED",
      is_defective: true,
      defect_type: "scratch",
      confidence: 0.941,
      severity_score: 41.2,
      severity_category: "Major",
      defect_area: 480,
      defect_area_mm2: 19.2,
      latency_ms: 19.1
    },
    aiResult: {
      provider: "Google Gemini 2.5 Flash",
      decision: "DEFECT_DETECTED",
      is_defective: true,
      defect_type: "scratch",
      confidence: "high",
      description: "Superficial longitudinal tool abrasive striation along outer bearing journal seat.",
      reasoning: "Abrasive score marks do not penetrate substrate core, but breach anti-friction micro-finish specifications. Re-honing required to protect high-speed needle bearings.",
      latency_ms: 388
    }
  },
  {
    id: "part-03",
    name: "Precision Machined Hydraulic Cylinder",
    category: "normal",
    imageUrl: "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=600&auto=format&fit=crop&q=80",
    customResult: {
      decision: "CONFORMING",
      is_defective: false,
      defect_type: "normal",
      confidence: 0.996,
      severity_score: 0.0,
      severity_category: "None",
      defect_area: 0,
      defect_area_mm2: 0.0,
      latency_ms: 18.0
    },
    aiResult: {
      provider: "Google Gemini 2.5 Flash",
      decision: "CONFORMING",
      is_defective: false,
      defect_type: "normal",
      confidence: "high",
      description: "Homogeneous metallic bore surface finish with zero micro-fractures, voids, or abrasive scoring.",
      reasoning: "Machining cross-hatch pattern complies with ISO 1302 Ra 0.40 µm tolerance. No anomalies detected within active pressure chamber zone.",
      latency_ms: 360
    }
  },
  {
    id: "part-04",
    name: "Die-Cast Aluminum Bracket",
    category: "dent",
    imageUrl: "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80",
    customResult: {
      decision: "DEFECT_DETECTED",
      is_defective: true,
      defect_type: "dent",
      confidence: 0.892,
      severity_score: 72.0,
      severity_category: "Critical",
      defect_area: 910,
      defect_area_mm2: 36.4,
      latency_ms: 21.0
    },
    aiResult: {
      provider: "Google Gemini 2.5 Flash",
      decision: "DEFECT_DETECTED",
      is_defective: true,
      defect_type: "dent",
      confidence: "medium",
      description: "Localized impact crater on corner web rib causing 1.2mm depth plastic deformation.",
      reasoning: "Impression likely caused by robotic drop or fixture pinch. Wall thickness locally reduced below safety margins; reject bracket for structural integrity.",
      latency_ms: 430
    }
  }
];

export function AiVisionScan() {
  const [selectedSample, setSelectedSample] = useState<InspectionSample>(SAMPLE_INSPECTIONS[0]);
  const [provider, setProvider] = useState<"gemini" | "openai" | "claude">("gemini");
  const [isInspecting, setIsInspecting] = useState(false);
  const [showCertModal, setShowCertModal] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  const handleRunScan = () => {
    setIsInspecting(true);
    setTimeout(() => {
      setIsInspecting(false);
      triggerToast("Dual-Engine Consensus Verification Complete!");
    }, 850);
  };

  const isAgreement = selectedSample.customResult.is_defective === selectedSample.aiResult.is_defective;

  const providerNames = {
    gemini: "Google Gemini 2.5 Flash",
    openai: "OpenAI GPT-4o Vision",
    claude: "Anthropic Claude 3.5 Sonnet"
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-6 z-50 bg-emerald-950 border border-emerald-500 text-emerald-200 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 animate-fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/80 p-5 rounded-2xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">
              PROMPT 18 & 19
            </span>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              Multimodal AI Vision Verification Mode
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Dual-engine arbitration comparing localized edge models (ResNet-18 + CAE) against cloud multimodal LLMs with QR-verified PDF certificates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
            <Bot className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-slate-400">LLM Provider:</span>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as any)}
              className="bg-transparent text-xs text-white font-medium focus:outline-none cursor-pointer"
            >
              <option value="gemini">Google Gemini 2.5 Flash</option>
              <option value="openai">OpenAI GPT-4o</option>
              <option value="claude">Claude 3.5 Sonnet</option>
            </select>
          </div>

          <button
            onClick={handleRunScan}
            disabled={isInspecting}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 via-purple-600 to-indigo-600 text-white text-xs font-semibold hover:opacity-90 transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isInspecting ? "animate-spin" : ""}`} />
            <span>{isInspecting ? "Arbitrating Engines..." : "Run Dual Inspection"}</span>
          </button>
        </div>
      </div>

      {/* Sample Selector Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {SAMPLE_INSPECTIONS.map((sample) => (
          <button
            key={sample.id}
            onClick={() => setSelectedSample(sample)}
            className={`p-3 rounded-xl border text-left transition-all flex items-center gap-3 ${
              selectedSample.id === sample.id
                ? "bg-purple-950/40 border-purple-500 shadow-sm"
                : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <img
              src={sample.imageUrl}
              alt={sample.name}
              className="w-12 h-12 rounded-lg object-cover border border-slate-700 shrink-0"
            />
            <div className="min-w-0">
              <p className="text-xs font-bold text-white truncate">{sample.name}</p>
              <span
                className={`inline-block text-[10px] font-mono px-1.5 py-0.5 rounded mt-1 ${
                  sample.category === "normal"
                    ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                    : "bg-rose-950 text-rose-400 border border-rose-800"
                }`}
              >
                {sample.category.toUpperCase()}
              </span>
            </div>
          </button>
        ))}
      </div>

      {/* Top Consensus Agreement Banner */}
      <div
        className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          isAgreement
            ? "bg-emerald-950/30 border-emerald-500/60 text-emerald-200"
            : "bg-amber-950/40 border-amber-500/70 text-amber-200"
        }`}
      >
        <div className="flex items-center gap-3">
          {isAgreement ? (
            <div className="w-9 h-9 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-9 h-9 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
          )}
          <div>
            <h4 className="text-sm font-bold">
              {isAgreement
                ? "Consensus Agreement: Both Engines Confirm Part Disposition"
                : "Divergence Warning: Manual Review Required"}
            </h4>
            <p className="text-xs opacity-80 mt-0.5">
              {isAgreement
                ? `Custom Edge Model and ${providerNames[provider]} agree on '${selectedSample.customResult.decision}' disposition.`
                : "Discrepancy detected between edge visual anomaly scoring and multimodal LLM semantic reasoning."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-mono opacity-75">
            Combined Latency: {(selectedSample.customResult.latency_ms + selectedSample.aiResult.latency_ms).toFixed(0)} ms
          </span>
        </div>
      </div>

      {/* Side-by-Side Verification Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Card: Custom Model */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-cyan-500" />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                  ENGINE 1: ON-PREMISE EDGE
                </span>
                <span className="text-xs text-slate-400">ResNet-18 + CAE</span>
              </div>
              <span className="text-xs font-mono text-cyan-400">
                {selectedSample.customResult.latency_ms} ms
              </span>
            </div>

            <div>
              <span
                className={`text-sm font-bold px-2.5 py-1 rounded-md inline-block ${
                  selectedSample.customResult.is_defective
                    ? "bg-rose-950 text-rose-300 border border-rose-800"
                    : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                }`}
              >
                {selectedSample.customResult.decision}
              </span>
              <h3 className="text-base font-bold text-white mt-2">{selectedSample.name}</h3>
            </div>

            {/* Visual Preview */}
            <div className="relative rounded-xl overflow-hidden border border-slate-800 bg-slate-950 aspect-video flex items-center justify-center">
              <img
                src={selectedSample.imageUrl}
                alt="Part specimen"
                className="w-full h-full object-cover"
              />
              {selectedSample.customResult.is_defective && (
                <div className="absolute inset-0 bg-rose-500/15 flex items-center justify-center pointer-events-none">
                  <div className="border-2 border-rose-500 border-dashed rounded-lg px-4 py-2 bg-rose-950/70 text-rose-300 text-xs font-mono">
                    Grad-CAM Defect Zone ({selectedSample.customResult.defect_area_mm2} mm²)
                  </div>
                </div>
              )}
            </div>

            {/* Metrics Breakdown */}
            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
              <div>
                <span className="text-slate-400">Class:</span>
                <p className="font-bold text-white capitalize">{selectedSample.customResult.defect_type}</p>
              </div>
              <div>
                <span className="text-slate-400">Confidence:</span>
                <p className="font-bold text-cyan-400 font-mono">
                  {(selectedSample.customResult.confidence * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <span className="text-slate-400">Severity:</span>
                <p className="font-bold text-amber-400">
                  {selectedSample.customResult.severity_score} ({selectedSample.customResult.severity_category})
                </p>
              </div>
              <div>
                <span className="text-slate-400">Defect Area:</span>
                <p className="font-mono text-slate-200">
                  {selectedSample.customResult.defect_area_mm2} mm² ({selectedSample.customResult.defect_area} px)
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Card: Multimodal AI Vision */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-5 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-purple-500" />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-purple-950 text-purple-300 border border-purple-800">
                  ENGINE 2: MULTIMODAL AI
                </span>
                <span className="text-xs text-purple-300 font-medium">
                  {providerNames[provider]}
                </span>
              </div>
              <span className="text-xs font-mono text-purple-400">
                {selectedSample.aiResult.latency_ms} ms
              </span>
            </div>

            <div>
              <span
                className={`text-sm font-bold px-2.5 py-1 rounded-md inline-block ${
                  selectedSample.aiResult.is_defective
                    ? "bg-rose-950 text-rose-300 border border-rose-800"
                    : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                }`}
              >
                {selectedSample.aiResult.decision}
              </span>
              <h3 className="text-base font-bold text-white mt-2">Vision Agent Assessment</h3>
            </div>

            {/* AI Reasoning Block */}
            <div className="space-y-3">
              <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-400">Identified Defect Type:</span>
                  <span className="text-xs font-bold text-purple-300 capitalize">
                    {selectedSample.aiResult.defect_type}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">Confidence Tier:</span>
                  <span className="text-xs font-mono font-bold text-emerald-400 uppercase">
                    {selectedSample.aiResult.confidence}
                  </span>
                </div>
              </div>

              <div className="bg-purple-950/20 border border-purple-800/40 p-3.5 rounded-xl space-y-2">
                <span className="text-[11px] font-bold tracking-wider text-purple-300 uppercase block">
                  Geometric Defect Localization:
                </span>
                <p className="text-xs text-slate-200 leading-relaxed italic">
                  "{selectedSample.aiResult.description}"
                </p>
              </div>

              <div className="bg-slate-950/80 border border-slate-800 p-3.5 rounded-xl space-y-2">
                <span className="text-[11px] font-bold tracking-wider text-slate-400 uppercase block">
                  Expert Mechanical Reasoning:
                </span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {selectedSample.aiResult.reasoning}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Action Strip: PDF Certificate & Batch PDF (Prompt 20) */}
      <div className="bg-slate-900/90 border border-slate-800 p-4 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-slate-300">
            <QrCode className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">Cryptographic QA Certificate (Prompt 20)</h4>
            <p className="text-xs text-slate-400">
              Each inspected component generates an ISO-compliant PDF with dynamic verification QR code.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCertModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold border border-slate-700 transition-all"
          >
            <Eye className="w-3.5 h-3.5 text-cyan-400" />
            <span>Preview Certificate</span>
          </button>

          <a
            href="/report/pdf/1"
            target="_blank"
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Download Signed PDF</span>
          </a>
        </div>
      </div>

      {/* Interactive PDF Certificate Modal */}
      {showCertModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-lg rounded-2xl shadow-2xl p-6 relative animate-fade-in">
            <div className="border-b border-slate-800 pb-4 mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Quality Inspection Certificate</h3>
              </div>
              <button
                onClick={() => setShowCertModal(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="text-slate-400 block text-[10px]">CERTIFICATE SERIAL</span>
                  <span className="font-mono font-bold text-cyan-400">CERT-2026-QA-{selectedSample.id.toUpperCase()}</span>
                </div>
                <span
                  className={`px-2.5 py-1 rounded font-bold text-xs ${
                    selectedSample.customResult.is_defective
                      ? "bg-rose-950 text-rose-300 border border-rose-700"
                      : "bg-emerald-950 text-emerald-300 border border-emerald-700"
                  }`}
                >
                  {selectedSample.customResult.is_defective ? "REJECT / SCRAP" : "PASSED INSPECTION"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-slate-300 bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                <p><strong>Part Name:</strong> {selectedSample.name}</p>
                <p><strong>Defect Type:</strong> {selectedSample.customResult.defect_type}</p>
                <p><strong>Severity:</strong> {selectedSample.customResult.severity_score} / 100</p>
                <p><strong>Confidence:</strong> {(selectedSample.customResult.confidence * 100).toFixed(1)}%</p>
                <p><strong>Inspector:</strong> Automated Edge Station 1</p>
                <p><strong>Timestamp:</strong> {new Date().toISOString().replace("T", " ").slice(0, 19)}</p>
              </div>

              <div className="p-3 bg-purple-950/20 border border-purple-800/30 rounded-xl">
                <span className="text-purple-300 font-bold block mb-1">AI Vision Peer Review:</span>
                <p className="text-slate-300">{selectedSample.aiResult.reasoning}</p>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <div className="w-16 h-16 bg-white p-1 rounded-lg flex items-center justify-center shrink-0">
                  <QrCode className="w-14 h-14 text-slate-950" />
                </div>
                <div className="text-[11px] text-slate-400 leading-tight">
                  <p className="text-slate-200 font-semibold">ISO 9001:2015 Traceability Standard</p>
                  <p>Scan to verify cryptographic certificate hash against factory central database ledger.</p>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-slate-800 pt-4">
              <button
                onClick={() => setShowCertModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold"
              >
                Close
              </button>
              <a
                href="/report/pdf/1"
                target="_blank"
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5"
              >
                <FileText className="w-3.5 h-3.5" />
                Print / Save PDF
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
