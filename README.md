# Vision-Based Defect Detection for Manufacturing Quality Inspection

A complete, production-grade industrial visual inspection system built with **Python**, **OpenCV**, **PyTorch**, and **scikit-learn**. The system detects defective versus normal parts, classifies the defect category, localizes the defective region using Grad-CAM and contour geometry, and performs multi-layer false-positive filtering.
---
## 🏭 Defect Categories Covered
1. **Normal** (Defect-free baseline product)
2. **Crack** (Jagged, branching micro-fractures)
3. **Scratch** (Linear/curved abrasions with specular highlights)
4. **Dent** (Localized 3D surface depression with directional illumination)
5. **Stain** (Organic, oil, or chemical surface residue)
6. **Discoloration** (Thermal oxidation or chemical hue shift)
7. **Dimensional Irregularity** (Edge deformities, burrs, chips, or asymmetric border distortion)

---

## 📁 Project Structure

```
.
├── data/
│   ├── raw/                  # Downloaded benchmarks (e.g. MVTec AD categories)
│   └── processed/            # Conditioned train/val/test splits with ground truth masks
├── src/
│   ├── __init__.py
│   ├── dataset.py            # Dataset downloader & synthetic OpenCV procedural generator
│   ├── preprocessing.py      # CLAHE (LAB), Bilateral Denoising, ROI Extraction, Albumentations
│   ├── anomaly_detection.py  # Conv-Autoencoder & Transfer-learning Binary Classifier
│   ├── defect_classifier.py  # Multi-class EfficientNet-B0 with Focal Loss & Imbalance weights
│   ├── localization.py       # Grad-CAM activation heatmaps & contour bounding boxes (px & mm)
│   ├── refinement.py         # Dual-consensus, morphological filter, TTA voting, borderline log
│   └── pipeline.py           # Unified 5-stage end-to-end inspection orchestrator
├── models/                   # Saved model checkpoints (.pth)
├── outputs/                  # Inspection overlays, Grad-CAM maps, confusion matrices, audit logs
├── notebooks/                # Walkthrough Jupyter notebooks for engineers
├── prepare_dataset.py        # Dataset preparation entry script
├── main.py                   # Master CLI interface
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🚀 Quickstart & Setup

### 1. Installation
```bash
# Create and activate a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### 2. Dataset Preparation (Prompt 0)
Prepare the dataset using either the synthetic procedural generator or download MVTec AD:
```bash
# Option A: Generate synthetic industrial dataset (default)
python main.py prepare --source synthetic --samples 60

# Option B: Download MVTec AD industrial benchmark category
python main.py prepare --source mvtec --category metal_nut
```

### 3. Image Preprocessing & Conditioning (Prompt 1)
Test aspect-ratio preserving letterboxing, LAB-space CLAHE, and bilateral filtering:
```bash
python main.py preprocess
# Output saved to: outputs/preprocessing_comparison.png
```

### 4. End-to-End Inspection Pipeline (Prompt 2, 3, 4, 5)
Run the inspection pipeline on test samples or a custom manufactured part:
```bash
# Run batch simulation demo
python main.py demo

# Inspect a specific manufacturing image
python main.py inspect --image path/to/part_image.png --sample_id PART_SERIAL_4091
```

---

## 🔬 Architectural Stages

### Stage 0: Dataset & Synthesis (`src/dataset.py`)
- **MVTec AD Downloader**: Downloads and unpacks official benchmarks (metal nut, bottle, tile, screw, cable, etc.).
- **OpenCV Synthetic Generator**: Procedurally injects realistic industrial defects with corresponding pixel-level ground truth binary masks.

### Stage 1: Preprocessing & Lighting Normalization (`src/preprocessing.py`)
- **CLAHE on L-Channel**: Converts to CIE LAB space, applies Contrast Limited Adaptive Histogram Equalization exclusively to Luminance ($L$) to balance severe factory lighting and shadows without oversaturating color channels.
- **Bilateral Filtering**: Smooths sensor noise while strictly preserving sharp crack boundaries.
- **Edge-Based ROI Extraction**: Isolates product body and discards conveyor belts and jig fixtures.
- **Albumentations**: Handles in-line rotational and illumination invariance.

### Stage 2: Anomaly Detection (`src/anomaly_detection.py`)
- **Convolutional Autoencoder (CAE)**: Trained exclusively on normal defect-free products.
- **Anomaly Score**: Hybrid MSE + SSIM reconstruction error.
- **Statistical Thresholding**: Calibrated using validation normal distribution ($\mu + k \cdot \sigma$) or ROC-AUC optimal threshold.
- **Transfer Learning Alternative**: Optional fine-tuned binary classifier switchable via config flag.

### Stage 3: Multi-Class Defect Classifier (`src/defect_classifier.py`)
- **Backbone**: EfficientNet-B0 / MobileNet-V2 with two-stage training (frozen head -> end-to-end fine-tuning).
- **Class Imbalance**: Mitigated using Focal Loss ($\gamma = 2.0$) or inverse class weights.
- **Output**: Defect category + normalized softmax probability distribution.
- **Metrics**: Normalized confusion matrix and per-class Precision / Recall / F1-score.

### Stage 4: Defect Localization (`src/localization.py`)
- **Grad-CAM**: Gradient-weighted class activation mapping targeting the final conv layer.
- **OpenCV Contour Analysis**: Thresholds activation map, applies `cv2.findContours`, extracts bounding boxes.
- **Physical Dimensional Calibration**: Converts area in square pixels to square millimeters ($mm^2$) using factory camera calibration ($mm/px$).

### Stage 5: Refinement & False-Positive Suppression (`src/refinement.py`)
- **Dual-Model Consensus**: Defect confirmed only when both Anomaly Detector and Classifier agree above threshold.
- **Morphological Noise Cleanup**: Opening removes isolated speckles; closing bridges micro-fractures; enforces minimum area threshold.
- **Test-Time Augmentation (TTA)**: 3-view voting (Original, Horizontal Flip, Rotated 10°) ensures defect persistence.
- **Borderline Quarantine Log**: Borderline or conflicted cases are quarantined into `outputs/borderline_review_queue.json` for human QA operator audit.

---

## 🐳 Production Containerization & Docker Compose (Prompt 16)

The project includes a multi-stage production Dockerfile and a multi-container `docker-compose.yml` service definition.

### 1. Run Everything Locally
To build the container image and launch the inspection server with persistence:
```bash
docker compose up --build
```
This starts:
- **`web`**: Python 3.11 slim runtime running production `gunicorn` (4 workers, port 5000)
- **`db`**: PostgreSQL 15 database service (optional, enabled if `DATABASE_TYPE=postgres`)

Access the workstation at:
- Web App & Scan: **`http://localhost:5000`**
- API Documentation: **`http://localhost:5000/api/docs`**
- Health Telemetry: **`http://localhost:5000/health`**

### 2. Pointing to Production Values via `.env`
Copy the template and configure your production credentials:
```bash
cp .env.example .env
```
Key production variables in `.env`:
- `SECRET_KEY`: Set a cryptographically secure key (e.g. `openssl rand -hex 32`)
- `DATABASE_TYPE`: Set to `postgres` to use PostgreSQL instead of SQLite
- `DATABASE_URL`: Set your managed PostgreSQL connection string
- `GEMINI_API_KEY`: Set for Multimodal AI Vision Scan mode (Prompt 18)
- `ALLOWED_ORIGINS`: Restrict CORS domains to your enterprise gateway
