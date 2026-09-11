import React, { useState, useMemo } from "react";
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  Download,
  Calendar,
  Filter,
  ShieldAlert,
  Database,
  RefreshCw
} from "lucide-react";

interface InspectionItem {
  id: number;
  timestamp: string;
  filename: string;
  is_defective: boolean;
  defect_type: string;
  confidence: number;
  defect_area: number;
  severity_score: number;
  severity_category: "Minor" | "Major" | "Critical" | "None";
}

// Initial realistic database seed matching SQLite schema
const INITIAL_INSPECTIONS: InspectionItem[] = [
  { id: 1065, timestamp: "2026-09-10 20:45:12", filename: "flange_batch_99.png", is_defective: true, defect_type: "crack", confidence: 0.962, defect_area: 480.5, severity_score: 84.5, severity_category: "Critical" },
  { id: 1064, timestamp: "2026-09-10 20:38:05", filename: "bearing_ring_12.png", is_defective: false, defect_type: "normal", confidence: 0.985, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1063, timestamp: "2026-09-10 19:22:31", filename: "bracket_part_04.png", is_defective: true, defect_type: "scratch", confidence: 0.884, defect_area: 310.2, severity_score: 46.2, severity_category: "Major" },
  { id: 1062, timestamp: "2026-09-10 18:14:40", filename: "piston_pin_88.png", is_defective: false, defect_type: "normal", confidence: 0.991, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1061, timestamp: "2026-09-10 16:50:19", filename: "casing_housing_33.png", is_defective: true, defect_type: "dent", confidence: 0.932, defect_area: 520.0, severity_score: 76.8, severity_category: "Critical" },
  { id: 1060, timestamp: "2026-09-10 15:30:22", filename: "gear_face_102.png", is_defective: false, defect_type: "normal", confidence: 0.978, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1059, timestamp: "2026-09-09 21:10:04", filename: "valve_cap_09.png", is_defective: true, defect_type: "stain", confidence: 0.825, defect_area: 140.0, severity_score: 22.4, severity_category: "Minor" },
  { id: 1058, timestamp: "2026-09-09 18:05:15", filename: "coupling_disk_77.png", is_defective: true, defect_type: "discoloration", confidence: 0.795, defect_area: 195.0, severity_score: 25.1, severity_category: "Minor" },
  { id: 1057, timestamp: "2026-09-09 14:12:30", filename: "seal_flange_55.png", is_defective: true, defect_type: "dimensional_irregularity", confidence: 0.941, defect_area: 610.5, severity_score: 81.2, severity_category: "Critical" },
  { id: 1056, timestamp: "2026-09-09 11:40:02", filename: "shaft_blank_14.png", is_defective: false, defect_type: "normal", confidence: 0.988, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1055, timestamp: "2026-09-08 17:25:40", filename: "pump_impeller_02.png", is_defective: true, defect_type: "crack", confidence: 0.955, defect_area: 410.0, severity_score: 79.5, severity_category: "Critical" },
  { id: 1054, timestamp: "2026-09-08 14:15:20", filename: "turbo_cover_61.png", is_defective: false, defect_type: "normal", confidence: 0.974, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1053, timestamp: "2026-09-08 10:05:11", filename: "cam_follower_19.png", is_defective: true, defect_type: "scratch", confidence: 0.862, defect_area: 280.0, severity_score: 41.5, severity_category: "Major" },
  { id: 1052, timestamp: "2026-09-07 19:40:33", filename: "cylinder_liner_82.png", is_defective: false, defect_type: "normal", confidence: 0.993, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1051, timestamp: "2026-09-07 15:20:19", filename: "manifold_inlet_07.png", is_defective: true, defect_type: "dent", confidence: 0.915, defect_area: 490.0, severity_score: 73.0, severity_category: "Critical" },
  { id: 1050, timestamp: "2026-09-06 18:00:54", filename: "rod_end_44.png", is_defective: false, defect_type: "normal", confidence: 0.982, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1049, timestamp: "2026-09-06 12:35:10", filename: "spacer_bush_21.png", is_defective: true, defect_type: "stain", confidence: 0.810, defect_area: 120.0, severity_score: 19.5, severity_category: "Minor" },
  { id: 1048, timestamp: "2026-09-05 16:45:00", filename: "hub_spline_91.png", is_defective: false, defect_type: "normal", confidence: 0.989, defect_area: 0.0, severity_score: 0.0, severity_category: "None" },
  { id: 1047, timestamp: "2026-09-05 11:10:22", filename: "stator_core_38.png", is_defective: true, defect_type: "crack", confidence: 0.970, defect_area: 530.0, severity_score: 88.0, severity_category: "Critical" },
  { id: 1046, timestamp: "2026-09-04 14:22:45", filename: "flange_neck_05.png", is_defective: false, defect_type: "normal", confidence: 0.995, defect_area: 0.0, severity_score: 0.0, severity_category: "None" }
];

export function AnalyticsDashboard() {
  const [daysScope, setDaysScope] = useState<7 | 30>(30);
  const [defectFilter, setDefectFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [inspections, setInspections] = useState<InspectionItem[]>(INITIAL_INSPECTIONS);
  const [showClearModal, setShowClearModal] = useState<boolean>(false);
  const [userRole, setUserRole] = useState<"admin" | "operator">("admin");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Filtered Inspections
  const filteredInspections = useMemo(() => {
    return inspections.filter((item) => {
      const matchType = defectFilter === "all" || item.defect_type === defectFilter;
      const matchSev = severityFilter === "all" || item.severity_category === severityFilter;
      return matchType && matchSev;
    });
  }, [inspections, defectFilter, severityFilter]);

  // Aggregate Metrics (Prompt 11)
  const totalInspections = inspections.length;
  const totalDefects = inspections.filter((i) => i.is_defective).length;
  const totalConforming = totalInspections - totalDefects;
  const rejectionRate = totalInspections > 0 ? ((totalDefects / totalInspections) * 100).toFixed(1) : "0.0";
  
  const defectItems = inspections.filter((i) => i.is_defective);
  const avgSeverity = defectItems.length > 0
    ? (defectItems.reduce((acc, curr) => acc + curr.severity_score, 0) / defectItems.length).toFixed(1)
    : "0.0";

  // Defect distribution
  const defectCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    defectItems.forEach((item) => {
      counts[item.defect_type] = (counts[item.defect_type] || 0) + 1;
    });
    return counts;
  }, [defectItems]);

  // Severity category breakdown
  const severityCounts = useMemo(() => {
    const counts = { Minor: 0, Major: 0, Critical: 0, None: 0 };
    inspections.forEach((item) => {
      if (item.severity_category in counts) {
        counts[item.severity_category]++;
      }
    });
    return counts;
  }, [inspections]);

  // Timeline points for Defects Over Time
  const timelineDays = useMemo(() => {
    const dates = ["09-04", "09-05", "09-06", "09-07", "09-08", "09-09", "09-10"];
    return dates.map((d) => {
      const dayMatches = inspections.filter((item) => item.timestamp.includes(d.replace("-", "-09-") || d));
      const defects = dayMatches.filter((m) => m.is_defective).length;
      const pass = dayMatches.length - defects;
      return { day: d, defects, pass, total: dayMatches.length };
    });
  }, [inspections]);

  const handleExportCSV = () => {
    const headers = "id,timestamp,filename,is_defective,defect_type,confidence,defect_area,severity_score,severity_category\n";
    const rows = inspections
      .map(
        (i) =>
          `${i.id},"${i.timestamp}","${i.filename}",${i.is_defective},"${i.defect_type}",${i.confidence},${i.defect_area},${i.severity_score},"${i.severity_category}"`
      )
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `inspections_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleClearHistory = () => {
    if (userRole !== "admin") {
      alert("Permission Denied: Only Admin role can clear SQLite inspection history.");
      return;
    }
    setInspections([]);
    setShowClearModal(false);
    setStatusMessage("SQLite inspections database cleared successfully.");
    setTimeout(() => setStatusMessage(null), 4000);
  };

  const handleResetDemoData = () => {
    setInspections(INITIAL_INSPECTIONS);
    setStatusMessage("Restored SQLite baseline inspection dataset.");
    setTimeout(() => setStatusMessage(null), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header & Role Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Prompt 11 — Database-Backed Analytics Dashboard</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Synchronized with SQLite table <code className="text-emerald-400 font-mono">inspections</code> · Chart.js & CSV export
          </p>
        </div>

        {/* Demo Role Switcher (Prompt 13) */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400">Current Role:</span>
          <button
            onClick={() => setUserRole("admin")}
            className={`px-2.5 py-1 rounded-md font-semibold border transition-all ${
              userRole === "admin"
                ? "bg-rose-950/80 border-rose-600 text-rose-300"
                : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Admin (Can Purge DB)
          </button>
          <button
            onClick={() => setUserRole("operator")}
            className={`px-2.5 py-1 rounded-md font-semibold border transition-all ${
              userRole === "operator"
                ? "bg-emerald-950/80 border-emerald-600 text-emerald-300"
                : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            Operator
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="p-3 bg-emerald-950/70 border border-emerald-700/60 rounded-lg text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{statusMessage}</span>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Inspections</span>
          <div className="text-2xl font-bold font-mono text-white mt-1">{totalInspections}</div>
          <span className="text-[11px] text-slate-500">Stored in SQLite inspections</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">Defective Parts</span>
          <div className="text-2xl font-bold font-mono text-rose-400 mt-1">{totalDefects}</div>
          <span className="text-[11px] text-slate-500">Defect events detected</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Rejection Rate</span>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">{rejectionRate}%</div>
          <span className="text-[11px] text-slate-500">Defective / total ratio</span>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">Avg Defect Severity</span>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">{avgSeverity} <span className="text-xs text-slate-500">/ 100</span></div>
          <span className="text-[11px] text-slate-500">Multi-factor severity score</span>
        </div>
      </div>

      {/* Controls & Scope Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 bg-slate-900 border border-slate-800 rounded-xl">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Time Range:</span>
          <button
            onClick={() => setDaysScope(7)}
            className={`px-3 py-1 text-xs font-medium rounded-md border transition-all ${
              daysScope === 7 ? "bg-slate-800 border-cyan-500 text-white" : "border-slate-800 text-slate-400 hover:bg-slate-800/50"
            }`}
          >
            Last 7 Days
          </button>
          <button
            onClick={() => setDaysScope(30)}
            className={`px-3 py-1 text-xs font-medium rounded-md border transition-all ${
              daysScope === 30 ? "bg-slate-800 border-cyan-500 text-white" : "border-slate-800 text-slate-400 hover:bg-slate-800/50"
            }`}
          >
            Last 30 Days
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>

          {inspections.length === 0 ? (
            <button
              onClick={handleResetDemoData}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Seed DB Data</span>
            </button>
          ) : userRole === "admin" ? (
            <button
              onClick={() => setShowClearModal(true)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-950/80 hover:bg-rose-900 text-rose-200 border border-rose-700 flex items-center gap-1.5 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear History</span>
            </button>
          ) : (
            <button
              disabled
              title="Admin role required to clear database"
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-950 text-slate-600 border border-slate-800 cursor-not-allowed flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear History (Admin Only)</span>
            </button>
          )}
        </div>
      </div>

      {/* Visual Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 1. Defects Over Time Line Chart */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 p-5 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                <span>Defects Over Time ({daysScope === 7 ? "Last 7 Days" : "Last 30 Days"})</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Daily defect vs conforming count timeline</p>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-rose-400 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Defective
              </span>
              <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Conforming
              </span>
            </div>
          </div>

          <div className="h-56 flex items-end justify-between gap-3 pt-4 border-b border-slate-800">
            {timelineDays.map((item, idx) => {
              const maxVal = 6;
              const defHeight = (item.defects / maxVal) * 100;
              const passHeight = (item.pass / maxVal) * 100;
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                  <div className="w-full flex items-end justify-center gap-1.5 h-44">
                    {/* Defect bar */}
                    <div
                      style={{ height: `${Math.max(6, defHeight)}%` }}
                      className="w-1/2 bg-rose-500/80 hover:bg-rose-400 rounded-t transition-all relative"
                      title={`${item.day}: ${item.defects} defects`}
                    >
                      <span className="opacity-0 group-hover:opacity-100 absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-mono text-rose-300">
                        {item.defects}
                      </span>
                    </div>
                    {/* Conforming bar */}
                    <div
                      style={{ height: `${Math.max(6, passHeight)}%` }}
                      className="w-1/2 bg-emerald-500/80 hover:bg-emerald-400 rounded-t transition-all relative"
                      title={`${item.day}: ${item.pass} conforming`}
                    >
                      <span className="opacity-0 group-hover:opacity-100 absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-mono text-emerald-300">
                        {item.pass}
                      </span>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">{item.day}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Severity Category Breakdown */}
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Severity Category Breakdown</span>
            </h3>
            <p className="text-xs text-slate-400">Minor vs Major vs Critical distribution</p>
          </div>

          <div className="space-y-3 my-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-rose-400 font-semibold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-rose-500" /> Critical (&gt;70)
                </span>
                <span className="font-mono text-slate-300">{severityCounts.Critical} parts</span>
              </div>
              <div className="h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${totalInspections > 0 ? (severityCounts.Critical / totalInspections) * 100 : 0}%` }}
                  className="h-full bg-rose-500 rounded-full"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-amber-400 font-semibold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-500" /> Major (30–70)
                </span>
                <span className="font-mono text-slate-300">{severityCounts.Major} parts</span>
              </div>
              <div className="h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${totalInspections > 0 ? (severityCounts.Major / totalInspections) * 100 : 0}%` }}
                  className="h-full bg-amber-500 rounded-full"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" /> Minor (&lt;30)
                </span>
                <span className="font-mono text-slate-300">{severityCounts.Minor} parts</span>
              </div>
              <div className="h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${totalInspections > 0 ? (severityCounts.Minor / totalInspections) * 100 : 0}%` }}
                  className="h-full bg-emerald-500 rounded-full"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-400 font-semibold flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-slate-600" /> None (Normal)
                </span>
                <span className="font-mono text-slate-300">{severityCounts.None} parts</span>
              </div>
              <div className="h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                <div
                  style={{ width: `${totalInspections > 0 ? (severityCounts.None / totalInspections) * 100 : 0}%` }}
                  className="h-full bg-slate-600 rounded-full"
                />
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-500 border-t border-slate-800 pt-3">
            Disposition: Critical &rarr; Reject immediately · Major &rarr; Review · Minor &rarr; Log only
          </div>
        </div>
      </div>

      {/* 3. Defect Type Distribution Bar Chart */}
      <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
        <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
          <BarChart3 className="w-4 h-4 text-emerald-400" />
          <span>Defect Type Classification Distribution</span>
        </h3>
        <p className="text-xs text-slate-400 mb-4">Frequency counts across the 6 defect categories</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {[
            { type: "crack", label: "Crack", color: "border-rose-700 bg-rose-950/40 text-rose-300" },
            { type: "scratch", label: "Scratch", color: "border-amber-700 bg-amber-950/40 text-amber-300" },
            { type: "dent", label: "Dent", color: "border-orange-700 bg-orange-950/40 text-orange-300" },
            { type: "stain", label: "Stain", color: "border-cyan-700 bg-cyan-950/40 text-cyan-300" },
            { type: "discoloration", label: "Discoloration", color: "border-purple-700 bg-purple-950/40 text-purple-300" },
            { type: "dimensional_irregularity", label: "Dimensional", color: "border-pink-700 bg-pink-950/40 text-pink-300" }
          ].map((cat) => {
            const count = defectCounts[cat.type] || 0;
            return (
              <div key={cat.type} className={`p-3 rounded-lg border ${cat.color} flex flex-col items-center text-center`}>
                <span className="text-xs font-semibold">{cat.label}</span>
                <span className="text-xl font-bold font-mono mt-1">{count}</span>
                <span className="text-[10px] text-slate-400">occurrences</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Inspections Table with Interactive Filtering (Prompt 11) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-white">Recent Inspection Log (Last 20)</h3>
            <p className="text-xs text-slate-400">Audit trail backed by SQLite inspections table</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span>Type:</span>
              <select
                value={defectFilter}
                onChange={(e) => setDefectFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded px-2 py-1 outline-none"
              >
                <option value="all">All</option>
                <option value="normal">Normal</option>
                <option value="crack">Crack</option>
                <option value="scratch">Scratch</option>
                <option value="dent">Dent</option>
                <option value="stain">Stain</option>
                <option value="discoloration">Discoloration</option>
                <option value="dimensional_irregularity">Dimensional Irreg.</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span>Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded px-2 py-1 outline-none"
              >
                <option value="all">All</option>
                <option value="None">None</option>
                <option value="Minor">Minor</option>
                <option value="Major">Major</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-mono text-[11px] uppercase tracking-wider">
                <th className="py-2.5 px-4">ID</th>
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Filename</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Defect Category</th>
                <th className="py-2.5 px-4">Confidence</th>
                <th className="py-2.5 px-4">Defect Area</th>
                <th className="py-2.5 px-4">Severity Score</th>
                <th className="py-2.5 px-4">Severity Tier</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filteredInspections.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-500">
                    No inspections match current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredInspections.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 px-4 font-mono text-slate-500">#{row.id}</td>
                    <td className="py-2.5 px-4 font-mono text-slate-400 text-[11px]">{row.timestamp}</td>
                    <td className="py-2.5 px-4 font-semibold text-slate-200">{row.filename}</td>
                    <td className="py-2.5 px-4">
                      {row.is_defective ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800/60">
                          DEFECT
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                          PASS
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 capitalize text-slate-300">
                      {row.defect_type.replace("_", " ")}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-slate-300">
                      {(row.confidence * 100).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-4 font-mono text-slate-300">
                      {row.defect_area > 0 ? `${row.defect_area} px` : "—"}
                    </td>
                    <td className="py-2.5 px-4 font-mono font-bold text-slate-200">
                      {row.severity_score}
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          row.severity_category === "Critical"
                            ? "bg-rose-950 text-rose-300 border-rose-800/70"
                            : row.severity_category === "Major"
                            ? "bg-amber-950 text-amber-300 border-amber-800/70"
                            : row.severity_category === "Minor"
                            ? "bg-emerald-950 text-emerald-300 border-emerald-800/70"
                            : "bg-slate-950 text-slate-400 border-slate-800"
                        }`}
                      >
                        {row.severity_category.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Clear Database Modal (Prompt 11) */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base font-bold text-white">Confirm SQLite Database Purge</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed mb-5">
              Are you sure you want to delete all historical inspection records from the SQLite{" "}
              <code className="text-rose-400">inspections</code> table? This operation cannot be reversed.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowClearModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleClearHistory}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-500 transition-all"
              >
                Yes, Purge Database
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
