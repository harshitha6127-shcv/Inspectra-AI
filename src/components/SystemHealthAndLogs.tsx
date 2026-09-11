import React, { useState, useEffect } from "react";
import {
  Activity,
  Server,
  HardDrive,
  Database,
  Cpu,
  FileText,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  ShieldCheck
} from "lucide-react";

interface LogEntry {
  id: string;
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR";
  logger: string;
  message: string;
}

const INITIAL_LOGS: LogEntry[] = [
  { id: "log-1", timestamp: "2026-09-10 20:50:01", level: "INFO", logger: "DefectInspectionApp", message: "Application logging initialized. Logs writing to /logs/app.log (Rotating: 10MB x 5 backups)" },
  { id: "log-2", timestamp: "2026-09-10 20:50:02", level: "INFO", logger: "DatabaseManager", message: "SQLite connection verified. Database path: /data/inspections.db" },
  { id: "log-3", timestamp: "2026-09-10 20:50:03", level: "INFO", logger: "Pipeline", message: "CAE Autoencoder and ResNet-18 models loaded successfully on device: cpu" },
  { id: "log-4", timestamp: "2026-09-10 20:51:14", level: "INFO", logger: "DefectInspectionApp", message: "User logged in: username='admin', role='admin'" },
  { id: "log-5", timestamp: "2026-09-10 20:52:30", level: "INFO", logger: "DefectInspectionApp", message: "[INSPECTION] user=admin filename=flange_batch_99.png is_defective=True type=crack conf=0.962 sev=84.5 (Critical) latency=18.4ms" },
  { id: "log-6", timestamp: "2026-09-10 20:53:45", level: "INFO", logger: "DefectInspectionApp", message: "[INSPECTION] user=admin filename=bearing_ring_12.png is_defective=False type=normal conf=0.985 sev=0.0 (None) latency=16.8ms" },
  { id: "log-7", timestamp: "2026-09-10 20:55:12", level: "WARNING", logger: "DefectInspectionApp", message: "Analyze rejected invalid file extension: 'spec_sheet.pdf' (Allowed: .jpg, .png, .bmp)" },
  { id: "log-8", timestamp: "2026-09-10 20:56:04", level: "INFO", logger: "DefectInspectionApp", message: "[INSPECTION] user=operator filename=casing_housing_33.png is_defective=True type=dent conf=0.932 sev=76.8 (Critical) latency=19.1ms" },
  { id: "log-9", timestamp: "2026-09-10 20:58:20", level: "INFO", logger: "DefectInspectionApp", message: "CSV Report generated: report_b9f2e411.csv (Count: 3 items)" },
  { id: "log-10", timestamp: "2026-09-10 20:59:02", level: "INFO", logger: "DefectInspectionApp", message: "Health check query executed: status=healthy, disk_free=84.2%" }
];

export function SystemHealthAndLogs() {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);
  const [filterLevel, setFilterLevel] = useState<"ALL" | "INFO" | "WARNING" | "ERROR">("ALL");
  const [uptimeSeconds, setUptimeSeconds] = useState<number>(3742);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setUptimeSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatUptime = (totalSec: number) => {
    const hours = Math.floor(totalSec / 3600);
    const mins = Math.floor((totalSec % 3600) / 60);
    const secs = totalSec % 60;
    return `${hours}h ${mins}m ${secs}s`;
  };

  const handleSimulateLog = () => {
    const newEntry: LogEntry = {
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
      level: "INFO",
      logger: "DefectInspectionApp",
      message: `[INSPECTION] user=admin filename=simulated_part_${Math.floor(Math.random() * 100)}.png is_defective=True type=scratch conf=0.891 sev=43.5 (Major) latency=17.9ms`
    };
    setLogs((prev) => [newEntry, ...prev]);
  };

  const filteredLogs = logs.filter((l) => filterLevel === "ALL" || l.level === filterLevel);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-bold text-white">Prompt 14 — Logging, Error Handling & System Health</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time <code className="text-emerald-400 font-mono">/health</code> endpoint telemetry · Rotating file logs in <code className="text-cyan-400 font-mono">logs/app.log</code>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSimulateLog}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-700 flex items-center gap-1.5 transition-all"
          >
            <span>+ Simulate Inspection Log</span>
          </button>
        </div>
      </div>

      {/* System Health Cards Grid (GET /health) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: App Status */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Service Status</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="w-3 h-3 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xl font-bold text-white">HEALTHY</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            Uptime: {formatUptime(uptimeSeconds)} · v1.0.0
          </div>
        </div>

        {/* Card 2: Deep Learning Models */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Vision Models</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-cyan-400 mt-2">4 Active Engines</div>
          <div className="text-[11px] text-slate-400 mt-2">
            CAE · Classifier · Grad-CAM · Morph
          </div>
        </div>

        {/* Card 3: SQLite Database */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">SQLite Database</span>
            <Database className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-400 mt-2">Connected</div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            Tables: inspections, users · WAL mode
          </div>
        </div>

        {/* Card 4: Uploads Storage Disk */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider">Disk Storage</span>
            <HardDrive className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-purple-400 mt-2">84.2% Free</div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            uploads/: 10MB limit per request
          </div>
        </div>
      </div>

      {/* Rotating Structured Log Stream (Prompt 14) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-950/60">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <div>
              <h3 className="text-sm font-bold text-white">Rotating Audit Log Stream</h3>
              <p className="text-xs text-slate-400">Live feed of /logs/app.log (RotatingFileHandler: 10MB max, 5 backups)</p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Filter Level:</span>
            {(["ALL", "INFO", "WARNING", "ERROR"] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setFilterLevel(lvl)}
                className={`px-2.5 py-1 rounded text-xs font-bold border transition-all ${
                  filterLevel === lvl
                    ? "bg-slate-800 border-cyan-500 text-white"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>

        {/* Console Viewport */}
        <div className="p-4 bg-slate-950 font-mono text-xs space-y-2 max-h-96 overflow-y-auto">
          {filteredLogs.map((item) => (
            <div key={item.id} className="flex items-start gap-2.5 leading-relaxed hover:bg-slate-900/60 p-1.5 rounded">
              <span className="text-slate-500 shrink-0 select-none">[{item.timestamp}]</span>
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] font-bold shrink-0 ${
                  item.level === "ERROR"
                    ? "bg-rose-950 text-rose-400 border border-rose-800"
                    : item.level === "WARNING"
                    ? "bg-amber-950 text-amber-400 border border-amber-800"
                    : "bg-emerald-950 text-emerald-400 border border-emerald-800"
                }`}
              >
                {item.level}
              </span>
              <span className="text-cyan-400 shrink-0">[{item.logger}]</span>
              <span className="text-slate-300 break-all">{item.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
