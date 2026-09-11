// static/live.js - Browser Webcam Ingestion & Live Auto-Capture (Prompt 10)

const videoFeed = document.getElementById("videoFeed");
const captureCanvas = document.getElementById("captureCanvas");
const captureBtn = document.getElementById("captureBtn");
const autoCaptureToggle = document.getElementById("autoCaptureToggle");
const cameraAlert = document.getElementById("cameraAlert");
const cameraAlertText = document.getElementById("cameraAlertText");
const streamDot = document.getElementById("streamDot");
const streamStatusText = document.getElementById("streamStatusText");
const cameraDeviceLabel = document.getElementById("cameraDeviceLabel");

const lastUpdated = document.getElementById("lastUpdated");
const liveStatusBanner = document.getElementById("liveStatusBanner");
const liveStatusBadge = document.getElementById("liveStatusBadge");
const liveDefectTitle = document.getElementById("liveDefectTitle");
const liveConfidence = document.getElementById("liveConfidence");
const liveSeverity = document.getElementById("liveSeverity");
const liveAction = document.getElementById("liveAction");
const liveAnomalyScore = document.getElementById("liveAnomalyScore");
const liveDefectArea = document.getElementById("liveDefectArea");
const liveInferenceTime = document.getElementById("liveInferenceTime");
const lastAnnotatedImg = document.getElementById("lastAnnotatedImg");
const noAnnotatedPlaceholder = document.getElementById("noAnnotatedPlaceholder");

let mediaStream = null;
let autoCaptureInterval = null;
let isAnalyzing = false;

// 1. Initialize Browser Webcam via getUserMedia
async function initCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "environment"
      },
      audio: false
    });

    videoFeed.srcObject = mediaStream;
    streamDot.classList.remove("hidden");
    streamStatusText.textContent = "Live Stream Active";

    // Retrieve active device track label
    const tracks = mediaStream.getVideoTracks();
    if (tracks.length > 0) {
      cameraDeviceLabel.textContent = tracks[0].label || "Webcam Video Device";
    }
  } catch (err) {
    console.warn("Camera access error:", err);
    cameraAlert.classList.remove("hidden");
    cameraAlertText.textContent = `Camera feed unavailable (${err.name}: ${err.message}). If testing in iframe or without webcam, manual upload remains active.`;
    streamDot.classList.remove("pulse");
    streamDot.style.background = "#94a3b8";
    streamStatusText.textContent = "Sensor Offline";
  }
}

// 2. Capture Single Frame and Analyze
async function captureAndAnalyze() {
  if (isAnalyzing) return; // Prevent concurrent requests
  isAnalyzing = true;
  captureBtn.disabled = true;

  try {
    const w = videoFeed.videoWidth || 640;
    const h = videoFeed.videoHeight || 480;

    captureCanvas.width = w;
    captureCanvas.height = h;
    const ctx = captureCanvas.getContext("2d");
    ctx.drawImage(videoFeed, 0, 0, w, h);

    // Convert canvas frame to Blob
    const blob = await new Promise((resolve) => {
      captureCanvas.toBlob(resolve, "image/png");
    });

    if (!blob) throw new Error("Failed to grab video frame.");

    const formData = new FormData();
    formData.append("image", blob, `live_frame_${Date.now()}.png`);

    const response = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Analysis error");
    }

    if (data.results && data.results.length > 0) {
      updateLiveInspectionDisplay(data.results[0]);
    }
  } catch (err) {
    console.error("Live analysis failed:", err);
  } finally {
    isAnalyzing = false;
    captureBtn.disabled = false;
  }
}

// 3. Update Inspection HUD
function updateLiveInspectionDisplay(res) {
  const isDefective = res.is_defective;
  const timestamp = new Date().toLocaleTimeString();
  lastUpdated.textContent = `Last frame evaluated at: ${timestamp}`;

  // Banner status
  liveStatusBanner.className = `live-banner ${isDefective ? "defective" : "pass"}`;
  liveStatusBadge.className = `status-badge ${isDefective ? "defective" : "pass"}`;
  liveStatusBadge.textContent = isDefective ? "DEFECTIVE" : "PASS";

  liveDefectTitle.textContent = isDefective
    ? `Defect: ${res.defect_type.replace("_", " ").toUpperCase()}`
    : "Conforming Component";

  liveConfidence.textContent = `${(res.confidence * 100).toFixed(1)}%`;

  // Metrics
  liveSeverity.textContent = `${res.severity_category} (${res.severity_score}/100)`;
  if (res.severity_category === "Critical") {
    liveSeverity.style.color = "#ef4444";
  } else if (res.severity_category === "Major") {
    liveSeverity.style.color = "#f59e0b";
  } else {
    liveSeverity.style.color = "#10b981";
  }

  liveAction.textContent = res.recommended_action;
  liveAnomalyScore.textContent = res.anomaly_score.toFixed(4);
  liveDefectArea.textContent = `${res.defect_area} px² (${res.defect_area_mm2.toFixed(2)} mm²)`;
  liveInferenceTime.textContent = `${res.inference_time_ms} ms`;

  // Annotated Frame Thumbnail
  if (res.annotated_image_base64) {
    lastAnnotatedImg.src = res.annotated_image_base64;
    lastAnnotatedImg.classList.remove("hidden");
    noAnnotatedPlaceholder.classList.add("hidden");
  }
}

// 4. Listeners & Auto-Capture Toggle
captureBtn.addEventListener("click", () => {
  captureAndAnalyze();
});

autoCaptureToggle.addEventListener("change", (e) => {
  if (e.target.checked) {
    // Run immediately once, then every 2000 ms
    captureAndAnalyze();
    autoCaptureInterval = setInterval(captureAndAnalyze, 2000);
  } else {
    if (autoCaptureInterval) {
      clearInterval(autoCaptureInterval);
      autoCaptureInterval = null;
    }
  }
});

// Start camera on page load
window.addEventListener("DOMContentLoaded", () => {
  initCamera();
});

// Clean up tracks when navigating away
window.addEventListener("beforeunload", () => {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
  if (autoCaptureInterval) {
    clearInterval(autoCaptureInterval);
  }
});
