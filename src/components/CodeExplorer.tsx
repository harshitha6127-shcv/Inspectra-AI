import React, { useState } from "react";
import { PROJECT_CODE_FILES, CodeFileMeta } from "../data/codeFiles";
import { Copy, Check, Download, FileCode, Terminal, ExternalLink } from "lucide-react";

export const CodeExplorer: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<CodeFileMeta>(PROJECT_CODE_FILES[0]);
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([selectedFile.code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = selectedFile.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const lines = selectedFile.code.split("\n");

  return (
    <div className="space-y-4">
      {/* File Navigation Tabs */}
      <div className="flex flex-wrap gap-2 bg-slate-900/90 border border-slate-800 p-2 rounded-xl">
        {PROJECT_CODE_FILES.map((file) => {
          const isSelected = file.path === selectedFile.path;
          return (
            <button
              key={file.path}
              onClick={() => setSelectedFile(file)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 transition-all ${
                isSelected
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "bg-slate-950/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>{file.name}</span>
              <span className="text-[10px] opacity-75 font-sans">({file.stage})</span>
            </button>
          );
        })}
      </div>

      {/* Code Viewer Panel */}
      <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/80 border-b border-slate-800 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono text-emerald-400 font-semibold">{selectedFile.path}</span>
            <span className="text-slate-400">· {selectedFile.description}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1.5 transition-colors text-xs font-medium"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied" : "Copy Code"}</span>
            </button>

            <button
              onClick={handleDownload}
              className="px-2.5 py-1 rounded bg-emerald-600/90 hover:bg-emerald-600 text-white flex items-center gap-1.5 transition-colors text-xs font-medium"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download File</span>
            </button>
          </div>
        </div>

        {/* Code Content with Line Numbers */}
        <div className="overflow-x-auto max-h-[600px] p-4 text-xs font-mono leading-relaxed text-slate-200">
          <table className="border-collapse w-full">
            <tbody>
              {lines.map((line, idx) => (
                <tr key={idx} className="hover:bg-slate-900/40">
                  <td className="pr-4 text-right select-none text-slate-600 font-mono w-10 text-[11px]">
                    {idx + 1}
                  </td>
                  <td className="whitespace-pre">{line}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Execution Instructions */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 flex items-center gap-3">
        <Terminal className="w-5 h-5 text-emerald-400 flex-shrink-0" />
        <div>
          <span className="font-semibold text-white">Direct Terminal Execution:</span> All Python scripts are located in the project repository root and <code className="text-emerald-300 font-mono">src/</code> folder. Run <code className="text-emerald-300 font-mono">python3 main.py demo</code> or <code className="text-emerald-300 font-mono">python3 main.py prepare --source synthetic</code>.
        </div>
      </div>
    </div>
  );
};
