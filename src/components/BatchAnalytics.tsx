import React, { useState } from "react";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Activity,
  FileSpreadsheet,
  Check,
  X
} from "lucide-react";

interface QuarantineItem {
  id: string;
  timestamp: string;
  sampleName: string;
  material: string;
  suspectedDefect: string;
  confidence: number;
  anomalyScore: number;
  reason: string;
  status: "PENDING_REVIEW" | "OPERATOR_APPROVED" | "OPERATOR_REJECTED";
}

export const BatchAnalytics: React.FC = () => {
  const [quarantineList, setQuarantineList] = useState<QuarantineItem[]>([
    {
      id: "QUAR-2026-0891",
      timestamp: "10:42:15",
      sampleName: "Turbine Blade Root #44",
      material: "Brushed Aluminum",
      suspectedDefect: "crack",
      confidence: 0.54,
      anomalyScore: 0.038,
      reason: "Borderline classifier confidence (54.0%) near 70% threshold",
      status: "PENDING_REVIEW"
    },
    {
      id: "QUAR-2026-0892",
      timestamp: "10:43:02",
      sampleName: "Machined Steel Flange #12",
      material: "Machined Steel",
      suspectedDefect: "scratch",
      confidence: 0.61,
      anomalyScore: 0.031,
      reason: "Model Discrepancy: AnomalyDetector=Normal, Classifier=Scratch",
      status: "PENDING_REVIEW"
    },
    {
      id: "QUAR-2026-0893",
      timestamp: "10:45:18",
      sampleName: "Die-Cast Housing Rim #8",
      material: "Brushed Aluminum",
      suspectedDefect: "dimensional_irregularity",
      confidence: 0.58,
      anomalyScore: 0.041,
      reason: "TTA Ensemble Inconsistent: 1 view Normal, 2 views Defective",
      status: "PENDING_REVIEW"
    }
  ]);

  const handleAction = (id: string, action: "OPERATOR_APPROVED" | "OPERATOR_REJECTED") => {
    setQuarantineList((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: action } : item))
    );
  };

  return (
    <div className="space-y-6">
      {/* High-level KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-400 mb-1">Batch Yield (Pass Rate)</div>
          <div className="text-2xl font-bold font-mono text-emerald-400">96.8%</div>
          <div className="text-[11px] text-slate-500 mt-1">484 / 500 Parts Conforming</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-400 mb-1">Defect Rejection Rate</div>
          <div className="text-2xl font-bold font-mono text-rose-400">2.6%</div>
          <div className="text-[11px] text-slate-500 mt-1">13 Parts Hard Rejected</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-400 mb-1">Quarantine (Human Audit)</div>
          <div className="text-2xl font-bold font-mono text-amber-400">0.6%</div>
          <div className="text-[11px] text-slate-500 mt-1">3 Borderline Cases Flagged</div>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="text-xs text-slate-400 mb-1">Mean Inspection Latency</div>
          <div className="text-2xl font-bold font-mono text-cyan-400">18.2 ms</div>
          <div className="text-[11px] text-slate-500 mt-1">54.9 FPS Line Speed</div>
        </div>
      </div>

      {/* Defect Pareto Chart & Breakdown */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <span className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
            Defect Category Distribution (Last 500 Parts)
          </span>
          <span className="text-xs text-slate-400">Batch #LOT-2026-X8</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2 text-xs">
            {[
              { type: "Surface Scratches", count: 6, pct: 37.5, color: "bg-rose-500" },
              { type: "Hairline Cracks", count: 4, pct: 25.0, color: "bg-orange-500" },
              { type: "Impact Dents", count: 3, pct: 18.7, color: "bg-amber-500" },
              { type: "Dimensional Edge Chips", count: 2, pct: 12.5, color: "bg-purple-500" },
              { type: "Thermal Discoloration", count: 1, pct: 6.3, color: "bg-blue-500" }
            ].map((d, i) => (
              <div key={i} className="space-y-1">
                <div className="flex justify-between text-slate-300">
                  <span>{d.type}</span>
                  <span className="font-mono text-slate-400">{d.count} units ({d.pct}%)</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                  <div className={`h-full ${d.color}`} style={{ width: `${d.pct}%` }} />
                </div>
              </div>
            ))}
          </div>

          <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800/80 text-xs space-y-3">
            <div className="font-semibold text-slate-200">Refinement Filter Impact:</div>
            <div className="text-slate-400 leading-relaxed">
              Without the Stage 5 Refinement Module (Dual Model Consensus + Morphological Opening + TTA),
              the false alarm rate was estimated at <strong className="text-rose-300">3.8%</strong> due to surface dust and lighting reflections.
            </div>
            <div className="text-emerald-400 font-medium">
              ✔ False positive escape rate reduced by 84% with morphological noise rejection and TTA 3-view voting.
            </div>
          </div>
        </div>
      </div>

      {/* Manual QA Quarantine Audit Queue */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <div className="text-xs font-semibold text-slate-200 uppercase tracking-wide">
              Borderline Quarantine Audit Queue (Prompt 5)
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              Items flagged for manual verification rather than hard classified
            </div>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-950 text-amber-300 border border-amber-700/50">
            {quarantineList.filter((q) => q.status === "PENDING_REVIEW").length} Action Needed
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                <th className="pb-2">Sample ID</th>
                <th className="pb-2">Time</th>
                <th className="pb-2">Material / Part</th>
                <th className="pb-2">Suspected Defect</th>
                <th className="pb-2">Conf / Score</th>
                <th className="pb-2">Quarantine Reason</th>
                <th className="pb-2 text-right">Operator Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {quarantineList.map((item) => (
                <tr key={item.id} className="hover:bg-slate-950/40">
                  <td className="py-3 font-mono text-slate-300 font-semibold">{item.id}</td>
                  <td className="py-3 font-mono text-slate-400">{item.timestamp}</td>
                  <td className="py-3 text-white font-medium">{item.sampleName}</td>
                  <td className="py-3 uppercase font-bold text-rose-400">{item.suspectedDefect}</td>
                  <td className="py-3 font-mono text-slate-300">
                    {(item.confidence * 100).toFixed(0)}% / {item.anomalyScore.toFixed(3)}
                  </td>
                  <td className="py-3 text-slate-400 max-w-xs truncate">{item.reason}</td>
                  <td className="py-3 text-right">
                    {item.status === "PENDING_REVIEW" ? (
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleAction(item.id, "OPERATOR_APPROVED")}
                          className="px-2 py-1 rounded bg-emerald-900/60 hover:bg-emerald-800 text-emerald-300 border border-emerald-700/50 flex items-center gap-1 font-medium text-[11px]"
                        >
                          <Check className="w-3 h-3" /> Approve (Pass)
                        </button>
                        <button
                          onClick={() => handleAction(item.id, "OPERATOR_REJECTED")}
                          className="px-2 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-300 border border-rose-700/50 flex items-center gap-1 font-medium text-[11px]"
                        >
                          <X className="w-3 h-3" /> Reject (Defect)
                        </button>
                      </div>
                    ) : item.status === "OPERATOR_APPROVED" ? (
                      <span className="text-emerald-400 font-medium inline-flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" /> Approved as Normal
                      </span>
                    ) : (
                      <span className="text-rose-400 font-medium inline-flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> Confirmed Defective
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
