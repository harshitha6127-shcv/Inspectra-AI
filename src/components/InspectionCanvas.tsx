import React, { useRef, useEffect } from "react";
import { PartSample, InspectionResultData } from "../types/inspection";

interface Props {
  sample: PartSample;
  inspection: InspectionResultData;
  activeView: "original" | "preprocessed" | "autoencoder_diff" | "gradcam" | "contours" | "final_hud";
  claheStrength: number;
  showBoundingBoxes: boolean;
  heatmapOpacity: number;
  mmPerPixel: number;
}

export const InspectionCanvas: React.FC<Props> = ({
  sample,
  inspection,
  activeView,
  claheStrength,
  showBoundingBoxes,
  heatmapOpacity,
  mmPerPixel
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = 320;
    const H = 320;
    canvas.width = W;
    canvas.height = H;

    // 1. Draw base material substrate
    ctx.save();
    if (sample.material === "Brushed Aluminum") {
      const grad = ctx.createLinearGradient(0, 0, W, H);
      grad.addColorStop(0, "#94a3b8");
      grad.addColorStop(0.5, "#cbd5e1");
      grad.addColorStop(1, "#64748b");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // Horizontal brushed machining lines
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1;
      for (let y = 0; y < H; y += 3) {
        ctx.beginPath();
        ctx.moveTo(0, y + (Math.sin(y * 10) * 0.5));
        ctx.lineTo(W, y);
        ctx.stroke();
      }
    } else if (sample.material === "Ceramic Tile") {
      ctx.fillStyle = "#f1f5f9";
      ctx.fillRect(0, 0, W, H);
      // Subtle speckles
      ctx.fillStyle = "rgba(100, 116, 139, 0.15)";
      for (let i = 0; i < 200; i++) {
        const sx = (i * 37) % W;
        const sy = (i * 73) % H;
        ctx.fillRect(sx, sy, 1.5, 1.5);
      }
    } else if (sample.material === "Machined Steel") {
      // Radial concentric toolmarks
      ctx.fillStyle = "#475569";
      ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = "rgba(226, 232, 240, 0.12)";
      ctx.lineWidth = 1;
      for (let r = 20; r < 240; r += 8) {
        ctx.beginPath();
        ctx.arc(W / 2, H / 2, r, 0, Math.PI * 2);
        ctx.stroke();
      }
    } else {
      // Molded polymer
      ctx.fillStyle = "#334155";
      ctx.fillRect(0, 0, W, H);
    }

    // 2. Lighting condition simulation
    if (sample.lightingCondition === "Directional Spotlight") {
      const lightGrad = ctx.createRadialGradient(80, 80, 20, 160, 160, 220);
      lightGrad.addColorStop(0, "rgba(255, 255, 255, 0.35)");
      lightGrad.addColorStop(1, "rgba(0, 0, 0, 0.45)");
      ctx.fillStyle = lightGrad;
      ctx.fillRect(0, 0, W, H);
    } else if (sample.lightingCondition === "Shadowed Conveyor") {
      const shadowGrad = ctx.createLinearGradient(0, 0, W, 0);
      shadowGrad.addColorStop(0, "rgba(0, 0, 0, 0.55)");
      shadowGrad.addColorStop(1, "rgba(255, 255, 255, 0.10)");
      ctx.fillStyle = shadowGrad;
      ctx.fillRect(0, 0, W, H);
    } else if (sample.lightingCondition === "High-Glare Flash") {
      const glare = ctx.createRadialGradient(180, 120, 5, 180, 120, 90);
      glare.addColorStop(0, "rgba(255, 255, 255, 0.75)");
      glare.addColorStop(0.3, "rgba(255, 255, 255, 0.3)");
      glare.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = glare;
      ctx.fillRect(0, 0, W, H);
    }

    // 3. Draw physical defect on workpiece
    const dp = sample.defectParams;
    const scale = W / 256;
    const cx = dp.cx * scale;
    const cy = dp.cy * scale;

    if (dp.type === "crack") {
      ctx.save();
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 2.5;
      ctx.lineCap = "round";
      ctx.lineJoin = "bevel";
      ctx.beginPath();
      ctx.moveTo(cx - 30, cy - 25);
      ctx.lineTo(cx - 10, cy - 10);
      ctx.lineTo(cx - 5, cy + 5);
      ctx.lineTo(cx + 15, cy + 18);
      ctx.lineTo(cx + 35, cy + 30);
      ctx.stroke();

      // Micro branch
      ctx.beginPath();
      ctx.moveTo(cx - 5, cy + 5);
      ctx.lineTo(cx + 12, cy - 5);
      ctx.stroke();
      ctx.restore();
    } else if (dp.type === "scratch") {
      ctx.save();
      ctx.strokeStyle = "rgba(248, 250, 252, 0.9)";
      ctx.shadowColor = "#020617";
      ctx.shadowBlur = 2;
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      const len = (dp.length || 40) * scale;
      ctx.moveTo(cx - len / 2, cy - len / 3);
      ctx.lineTo(cx + len / 2, cy + len / 3);
      ctx.stroke();
      ctx.restore();
    } else if (dp.type === "dent") {
      ctx.save();
      const dentGrad = ctx.createRadialGradient(cx - 6, cy - 6, 2, cx, cy, 26);
      dentGrad.addColorStop(0, "rgba(0, 0, 0, 0.75)");
      dentGrad.addColorStop(0.6, "rgba(51, 65, 85, 0.5)");
      dentGrad.addColorStop(1, "rgba(255, 255, 255, 0.3)");
      ctx.fillStyle = dentGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, 26, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    } else if (dp.type === "stain") {
      ctx.save();
      ctx.fillStyle = "rgba(120, 53, 15, 0.55)";
      ctx.beginPath();
      ctx.ellipse(cx, cy, 32, 22, 0.4, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    } else if (dp.type === "discoloration") {
      ctx.save();
      const discGrad = ctx.createRadialGradient(cx, cy, 4, cx, cy, 45);
      discGrad.addColorStop(0, "rgba(168, 85, 247, 0.6)");
      discGrad.addColorStop(0.5, "rgba(59, 130, 246, 0.4)");
      discGrad.addColorStop(1, "rgba(234, 179, 8, 0)");
      ctx.fillStyle = discGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, 45, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    } else if (dp.type === "dimensional_irregularity") {
      ctx.save();
      ctx.fillStyle = "#020617";
      ctx.beginPath();
      ctx.arc(cx, cy, 28, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // 4. View-specific overlays
    if (activeView === "preprocessed") {
      // CLAHE high-contrast enhancement filter
      const imgData = ctx.getImageData(0, 0, W, H);
      const data = imgData.data;
      const factor = 1.0 + (claheStrength * 0.25);
      for (let i = 0; i < data.length; i += 4) {
        data[i] = Math.min(255, Math.max(0, (data[i] - 128) * factor + 128));
        data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - 128) * factor + 128));
        data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - 128) * factor + 128));
      }
      ctx.putImageData(imgData, 0, 0);

      // Grid overlay
      ctx.strokeStyle = "rgba(16, 185, 129, 0.15)";
      ctx.lineWidth = 1;
      for (let x = 0; x < W; x += 32) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      }
      for (let y = 0; y < H; y += 32) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      }
    } else if (activeView === "autoencoder_diff" || activeView === "gradcam") {
      // Anomaly Heatmap / Grad-CAM pseudo-color overlay
      ctx.save();
      if (dp.type !== "normal") {
        const hmGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, 60);
        hmGrad.addColorStop(0, `rgba(239, 68, 68, ${heatmapOpacity * 0.95})`);
        hmGrad.addColorStop(0.3, `rgba(245, 158, 11, ${heatmapOpacity * 0.8})`);
        hmGrad.addColorStop(0.6, `rgba(16, 185, 129, ${heatmapOpacity * 0.5})`);
        hmGrad.addColorStop(1, `rgba(59, 130, 246, 0)`);

        ctx.fillStyle = hmGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, 60, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    } else if (activeView === "contours") {
      // Morphological contour boundaries
      if (dp.type !== "normal") {
        ctx.save();
        ctx.strokeStyle = "#06b6d4";
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.arc(cx, cy, 34, 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = "rgba(6, 182, 212, 0.2)";
        ctx.fill();
        ctx.restore();
      }
    }

    // 5. Bounding boxes & Severity-coded annotations (Prompts 7 & 9)
    if (showBoundingBoxes && inspection.regions.length > 0) {
      ctx.save();
      const sevCat = inspection.severityCategory || "None";
      const boxColor = sevCat === "Critical" ? "#ef4444" : sevCat === "Major" ? "#f59e0b" : "#22c55e";

      inspection.regions.forEach((r, idx) => {
        const rx = r.x * scale;
        const ry = r.y * scale;
        const rw = r.width * scale;
        const rh = r.height * scale;

        // Bounding box border with severity color
        ctx.strokeStyle = boxColor;
        ctx.lineWidth = 2.5;
        ctx.strokeRect(rx, ry, rw, rh);

        // Corner tick marks
        const tick = 6;
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        // Top-left
        ctx.beginPath(); ctx.moveTo(rx, ry + tick); ctx.lineTo(rx, ry); ctx.lineTo(rx + tick, ry); ctx.stroke();
        // Bottom-right
        ctx.beginPath(); ctx.moveTo(rx + rw, ry + rh - tick); ctx.lineTo(rx + rw, ry + rh); ctx.lineTo(rx + rw - tick, ry + rh); ctx.stroke();

        // Label Badge with Severity Category
        const badgeText = `#${idx + 1} ${sample.defectParams.type.toUpperCase()} | ${(r.areaPx * (mmPerPixel ** 2)).toFixed(1)}mm² [${sevCat.toUpperCase()}]`;
        ctx.font = "bold 10px monospace";
        const textWidth = ctx.measureText(badgeText).width;
        ctx.fillStyle = boxColor;
        ctx.fillRect(rx, Math.max(16, ry - 18), textWidth + 8, 16);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(badgeText, rx + 4, Math.max(16, ry - 18) + 12);
      });
      ctx.restore();
    }

    // 6. HUD Header Banner if final view
    if (activeView === "final_hud") {
      ctx.save();
      const isPass = inspection.decision === "PASS";
      const isReview = inspection.decision === "REVIEW_REQUIRED";
      const sevCat = inspection.severityCategory || "None";
      const headerBg = isPass
        ? "rgba(16, 185, 129, 0.95)"
        : sevCat === "Critical"
        ? "rgba(239, 68, 68, 0.95)"
        : isReview
        ? "rgba(245, 158, 11, 0.95)"
        : "rgba(239, 68, 68, 0.95)";

      ctx.fillStyle = headerBg;
      ctx.fillRect(0, 0, W, 28);

      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 11px system-ui, sans-serif";
      const title = isPass
        ? "✔ INSPECTION PASS — CONFORMING"
        : `✖ [${sevCat.toUpperCase()}] DEFECT: ${inspection.detectedType.toUpperCase()} (Score: ${inspection.severityScore})`;
      ctx.fillText(title, 8, 18);

      ctx.font = "bold 10px monospace";
      ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
      const confText = `${(inspection.overallConfidence * 100).toFixed(1)}%`;
      ctx.fillText(confText, W - ctx.measureText(confText).width - 8, 18);
      ctx.restore();
    }

    ctx.restore();
  }, [sample, inspection, activeView, claheStrength, showBoundingBoxes, heatmapOpacity, mmPerPixel]);

  return (
    <div className="relative rounded-lg overflow-hidden border border-slate-700/60 shadow-xl bg-slate-950 flex items-center justify-center">
      <canvas
        ref={canvasRef}
        className="w-full max-w-[340px] aspect-square object-contain block"
      />
    </div>
  );
};
