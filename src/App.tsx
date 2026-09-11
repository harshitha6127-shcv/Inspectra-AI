import React, { useState } from "react";
import {
  Eye,
  Layers,
  Code2,
  BarChart3,
  Camera,
  Activity,
  Award,
  ShieldCheck,
  Shield,
  Database,
  Terminal
} from "lucide-react";
import { InspectionStation } from "./components/InspectionStation";
import { PipelineDeepDive } from "./components/PipelineDeepDive";
import { CodeExplorer } from "./components/CodeExplorer";
import { BatchAnalytics } from "./components/BatchAnalytics";
import { LiveCameraInspection } from "./components/LiveCameraInspection";
import { EvaluationBenchmark } from "./components/EvaluationBenchmark";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";
import { DedicatedCameraScan } from "./components/DedicatedCameraScan";
import { AuthManagement } from "./components/AuthManagement";
import { SystemHealthAndLogs } from "./components/SystemHealthAndLogs";
import { AutomatedTestSuite } from "./components/AutomatedTestSuite";
import { AiVisionScan } from "./components/AiVisionScan";
import { DeploymentAndProduction } from "./components/DeploymentAndProduction";
import { Sparkles, Server } from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState<
    "station" | "scan" | "ai_scan" | "dashboard" | "deploy" | "auth" | "health" | "tests" | "pipeline" | "code"
  >("station");

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-black">
      {/* Top Industrial Workstation Header */}
      <header className="border-b border-slate-800/90 bg-slate-900/95 sticky top-0 z-40 backdrop-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center text-slate-950 shadow-md shadow-emerald-500/10">
              <Eye className="w-5 h-5 text-slate-950 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-white tracking-tight">
                  Inspectra AI
                </h1>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                  Ai powered visual inspection
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Ai powered visual inspection · Manufacturing Quality Workstation · OpenCV, PyTorch, Multimodal AI & QA Reporting
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex flex-wrap items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab("station")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "station"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Inspection Station</span>
            </button>

            <button
              onClick={() => setActiveTab("ai_scan")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "ai_scan"
                  ? "bg-purple-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-200" />
              <span>AI Vision Scan (P18)</span>
            </button>

            <button
              onClick={() => setActiveTab("scan")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "scan"
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Camera Scan (P12)</span>
            </button>

            <button
              onClick={() => setActiveTab("dashboard")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "dashboard"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Dashboard & Reports</span>
            </button>

            <button
              onClick={() => setActiveTab("deploy")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "deploy"
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Server className="w-3.5 h-3.5" />
              <span>Deploy & Docs (P16-17)</span>
            </button>

            <button
              onClick={() => setActiveTab("auth")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "auth"
                  ? "bg-rose-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Auth & RBAC (P13)</span>
            </button>

            <button
              onClick={() => setActiveTab("health")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "health"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Health & Logs (P14)</span>
            </button>

            <button
              onClick={() => setActiveTab("tests")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "tests"
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Pytest Suite (P15)</span>
            </button>

            <button
              onClick={() => setActiveTab("pipeline")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "pipeline"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Pipeline</span>
            </button>

            <button
              onClick={() => setActiveTab("code")}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                activeTab === "code"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              <span>Code</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {activeTab === "station" && <InspectionStation />}
        {activeTab === "ai_scan" && <AiVisionScan />}
        {activeTab === "scan" && <DedicatedCameraScan />}
        {activeTab === "dashboard" && <AnalyticsDashboard />}
        {activeTab === "deploy" && <DeploymentAndProduction />}
        {activeTab === "auth" && <AuthManagement />}
        {activeTab === "health" && <SystemHealthAndLogs />}
        {activeTab === "tests" && <AutomatedTestSuite />}
        {activeTab === "pipeline" && <PipelineDeepDive />}
        {activeTab === "code" && <CodeExplorer />}
      </main>

      {/* Industrial Inspection Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/70 py-4 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-slate-300 font-medium">Production Inspection Ready:</span>
            <span>CLI (`main.py --input`), Flask (`src/app.py`), Tests (`pytest -v`)</span>
          </div>

          <div className="flex items-center gap-4 font-mono text-[11px] text-slate-400">
            <span>SQLite Database</span>
            <span>·</span>
            <span>RBAC Auth</span>
            <span>·</span>
            <span>Rotating File Logging</span>
            <span>·</span>
            <span>Pytest Suite</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
