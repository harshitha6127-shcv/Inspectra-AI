// static/main.js - Drag-and-Drop Upload & Batch Inspection Controller

let selectedFiles = [];

const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const analyzeBtn = document.getElementById("analyzeBtn");
const clearBtn = document.getElementById("clearBtn");
const loadingIndicator = document.getElementById("loadingIndicator");
const errorBox = document.getElementById("errorBox");
const errorMessage = document.getElementById("errorMessage");

const resultCard = document.getElementById("resultCard");
const resultBadge = document.getElementById("resultBadge");
const resultTitle = document.getElementById("resultTitle");
const resultConfidence = document.getElementById("resultConfidence");
const annotatedImage = document.getElementById("annotatedImage");
const mDefectType = document.getElementById("mDefectType");
const mSeverityScore = document.getElementById("mSeverityScore");
const mSeverityCat = document.getElementById("mSeverityCat");
const mAction = document.getElementById("mAction");
const mAnomalyScore = document.getElementById("mAnomalyScore");
const mDefectArea = document.getElementById("mDefectArea");
const mInferenceTime = document.getElementById("mInferenceTime");

const batchSection = document.getElementById("batchSection");
const batchSubtitle = document.getElementById("batchSubtitle");
const batchTableBody = document.getElementById("batchTableBody");
const downloadReportBtn = document.getElementById("downloadReportBtn");

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "bmp"];

// 1. Drop Zone Event Listeners
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
    handleFiles(e.dataTransfer.files);
  }
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleFiles(e.target.files);
  }
});

clearBtn.addEventListener("click", () => {
  selectedFiles = [];
  updateFileUI();
});

function showError(msg) {
  errorMessage.textContent = msg;
  errorBox.classList.remove("hidden");
}

function closeError() {
  errorBox.classList.add("hidden");
}

function handleFiles(files) {
  closeError();
  const validFiles = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const ext = file.name.split(".").pop().toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      showError(`File "${file.name}" has an invalid extension. Only .jpg, .png, and .bmp are accepted.`);
      continue;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      showError(`File "${file.name}" exceeds the 10 MB maximum upload limit.`);
      continue;
    }

    validFiles.push(file);
  }

  // Append new files without duplicates by name
  validFiles.forEach((newFile) => {
    if (!selectedFiles.some((f) => f.name === newFile.name && f.size === newFile.size)) {
      selectedFiles.push(newFile);
    }
  });

  updateFileUI();
}

function updateFileUI() {
  fileList.innerHTML = "";

  if (selectedFiles.length === 0) {
    fileList.classList.add("hidden");
    analyzeBtn.disabled = true;
    clearBtn.classList.add("hidden");
    return;
  }

  fileList.classList.remove("hidden");
  analyzeBtn.disabled = false;
  clearBtn.classList.remove("hidden");

  selectedFiles.forEach((file, index) => {
    const chip = document.createElement("div");
    chip.className = "file-chip";
    chip.innerHTML = `
      <span>📄 ${file.name} (${(file.size / 1024).toFixed(1)} KB)</span>
      <span class="file-chip-remove" onclick="removeFile(${index})">&times;</span>
    `;
    fileList.appendChild(chip);
  });
}

window.removeFile = function (index) {
  selectedFiles.splice(index, 1);
  updateFileUI();
};

// 2. Analyze Execution
analyzeBtn.addEventListener("click", async () => {
  if (selectedFiles.length === 0) return;

  closeError();
  loadingIndicator.classList.remove("hidden");
  resultCard.classList.add("hidden");
  batchSection.classList.add("hidden");
  analyzeBtn.disabled = true;

  const formData = new FormData();
  selectedFiles.forEach((file) => {
    formData.append("images", file);
  });

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok || data.error) {
      throw new Error(data.error || "Inspection analysis failed on backend.");
    }

    renderResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    loadingIndicator.classList.add("hidden");
    analyzeBtn.disabled = false;
  }
});

// 3. Render Inspection Output
function renderResults(data) {
  const results = data.results || [];
  if (results.length === 0) return;

  // Single Result Inspector (Shows first or selected item)
  const primary = results[0];
  displayPrimaryResult(primary);

  // If batch mode (>1 items), populate batch table
  if (results.length > 1) {
    batchSubtitle.textContent = `Inspected ${results.length} parts in batch #${data.batch_id}`;
    downloadReportBtn.href = data.report_url || `/report/${data.batch_id}`;
    batchTableBody.innerHTML = "";

    results.forEach((item, idx) => {
      const tr = document.createElement("tr");
      const isDefective = item.is_defective;
      const statusBadge = isDefective
        ? `<span class="status-badge defective">DEFECT</span>`
        : `<span class="status-badge pass">PASS</span>`;

      const sevColor = item.severity_category === "Critical" ? "#ef4444" : item.severity_category === "Major" ? "#f59e0b" : "#10b981";

      tr.innerHTML = `
        <td>
          <img src="${item.annotated_image_base64}" class="thumb-img" alt="${item.filename}" onclick='displayPrimaryResult(${JSON.stringify(item)})' style="cursor:pointer;">
        </td>
        <td class="font-mono text-muted">${item.filename}</td>
        <td>${statusBadge}</td>
        <td class="capitalize font-semibold">${item.defect_type.replace("_", " ")}</td>
        <td style="color: ${sevColor}; font-weight: bold;">${item.severity_category}</td>
        <td class="font-mono">${(item.confidence * 100).toFixed(1)}%</td>
        <td class="font-mono">${item.defect_area_mm2.toFixed(2)}</td>
        <td>
          <button class="btn btn-outline" style="padding:4px 8px; font-size:11px;" onclick='displayPrimaryResult(${JSON.stringify(item)})'>
            Inspect
          </button>
        </td>
      `;
      batchTableBody.appendChild(tr);
    });

    batchSection.classList.remove("hidden");
  }
}

window.displayPrimaryResult = function (res) {
  resultCard.classList.remove("hidden");
  resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  const isDefective = res.is_defective;
  resultBadge.className = `status-badge ${isDefective ? "defective" : "pass"}`;
  resultBadge.textContent = isDefective ? `DEFECT DETECTED (${res.decision})` : "CONFORMING (PASS)";

  resultTitle.textContent = res.filename;
  resultConfidence.textContent = `${(res.confidence * 100).toFixed(1)}%`;
  annotatedImage.src = res.annotated_image_base64;

  mDefectType.textContent = res.defect_type.replace("_", " ");
  mSeverityScore.textContent = `${res.severity_score} / 100`;
  mSeverityCat.textContent = res.severity_category;

  // Severity color
  if (res.severity_category === "Critical") {
    mSeverityCat.style.color = "#ef4444";
  } else if (res.severity_category === "Major") {
    mSeverityCat.style.color = "#f59e0b";
  } else {
    mSeverityCat.style.color = "#10b981";
  }

  mAction.textContent = res.recommended_action;
  mAnomalyScore.textContent = res.anomaly_score.toFixed(4);
  mDefectArea.textContent = `${res.defect_area} px² (${res.defect_area_mm2.toFixed(2)} mm²)`;
  mInferenceTime.textContent = `${res.inference_time_ms} ms`;
};
