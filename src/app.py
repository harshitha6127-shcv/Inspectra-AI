"""
src/app.py - Production Flask Web Application for Defect Detection
===================================================================
Implements:
- Prompt 8: Single-page image upload & reporting web interface
- Prompt 10: Browser-based live camera inspection stream (/live route)
- Prompt 11: SQLite-backed Analytics Dashboard (/dashboard, /api/dashboard-data, /export-csv, /clear-history)
- Prompt 12: Dedicated Camera Scan page (/scan) with snapshot capture & analyze
- Prompt 13: Authentication & Role-based access (/login, /register, /logout, admin vs operator permissions)
- Prompt 14: Structured rotating logging, upload validation, /health check, global error handlers
"""

import os
import sys
import io
import time
import uuid
import base64
import csv
import shutil
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps
from typing import Dict, Any, List, Optional

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_file,
    redirect,
    url_for,
    session,
    Response,
    flash
)
from werkzeug.utils import secure_filename
import cv2
import numpy as np

# Ensure src/ is on Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pipeline import run_inspection
from models import db, User
from version import get_version_info
from ai_vision_scan import analyze_with_ai
from report_generator import generate_pdf_report, generate_batch_pdf_report
from qr_generator import generate_qr_png_bytes, generate_qr_svg, generate_qr_data_url

# Paths relative to project root
ROOT_DIR = os.path.dirname(current_dir)
TEMPLATES_DIR = os.path.join(ROOT_DIR, "templates")
STATIC_DIR = os.path.join(ROOT_DIR, "static")
UPLOAD_FOLDER = os.path.join(ROOT_DIR, "uploads")
REPORTS_FOLDER = os.path.join(ROOT_DIR, "outputs", "reports")
LOGS_DIR = os.path.join(ROOT_DIR, "logs")

for d in [UPLOAD_FOLDER, REPORTS_FOLDER, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

APP_START_TIME = time.time()

# -----------------------------------------------------------------------------
# Structured Logging Setup (Prompt 14)
# -----------------------------------------------------------------------------
logger = logging.getLogger("DefectInspectionApp")
logger.setLevel(logging.INFO)

# Formatter
log_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 1. Rotating File Handler (10MB per file, 5 backup files)
log_file_path = os.path.join(LOGS_DIR, "app.log")
file_handler = RotatingFileHandler(
    log_file_path,
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# 2. Console Stream Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

logger.info("Application logging initialized. Logs writing to %s", log_file_path)

# -----------------------------------------------------------------------------
# Flask Application Initialization & Config
# -----------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

app.secret_key = os.environ.get("SECRET_KEY", "industrial-defect-inspection-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit (Prompt 14)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp"}

# In-memory batch report cache for temporary CSV and PDF download
BATCH_REPORTS: Dict[str, Dict[str, Any]] = {}

# -----------------------------------------------------------------------------
# CORS Configuration (Prompt 17)
# -----------------------------------------------------------------------------
try:
    from flask_cors import CORS
    raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5000")
    origins_list = [o.strip() for o in raw_origins.split(",") if o.strip()]
    CORS(app, origins=origins_list, supports_credentials=True)
    logger.info("CORS initialized with allowed origins: %s", origins_list)
except ImportError:
    logger.warning("flask_cors not installed; relying on default CORS headers.")

# -----------------------------------------------------------------------------
# Rate Limiting Configuration (Prompt 17)
# -----------------------------------------------------------------------------
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["120 per minute"],
        storage_uri="memory://"
    )
    logger.info("Flask-Limiter initialized with memory storage.")
except ImportError:
    class DummyLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()
    logger.warning("flask_limiter not installed; using no-op dummy limiter.")



def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -----------------------------------------------------------------------------
# Authentication & Role Protection Helpers (Prompt 13)
# -----------------------------------------------------------------------------
def get_current_user() -> Optional[User]:
    """Retrieves the active logged-in user from the session, if present."""
    user_id = session.get("user_id")
    if user_id:
        return db.get_user_by_id(user_id)
    return None


def login_required(f):
    """Decorator ensuring route requires an authenticated user session."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith("/api/") or request.path == "/analyze":
                return jsonify({
                    "error": "Authentication required. Please log in.",
                    "code": 401
                }), 401
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator ensuring route requires an 'admin' role (Prompt 13)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required.", "code": 401}), 401
            return redirect(url_for("login", next=request.url))
        if not user.is_admin():
            logger.warning("Access denied: User '%s' (role: %s) attempted admin action on %s", user.username, user.role, request.path)
            if request.is_json or request.path.startswith("/api/") or request.method == "POST":
                return jsonify({
                    "error": "Forbidden: Admin role required for this operation.",
                    "code": 403
                }), 403
            return render_template("error.html", error_code=403, message="Admin privileges required to perform this action."), 403
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_user():
    """Injects current_user into all Jinja templates."""
    return {"current_user": get_current_user()}


# -----------------------------------------------------------------------------
# Authentication Routes (Prompt 13 & 17)
# -----------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def login():
    """User authentication route."""
    if get_current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.get_user_by_username(username)
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            logger.info("User logged in: username='%s', role='%s'", user.username, user.role)

            next_url = request.args.get("next")
            return redirect(next_url or url_for("index"))
        else:
            logger.warning("Failed login attempt for username: '%s'", username)
            flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User self-registration route (default role: operator)."""
    if get_current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "operator").strip().lower()

        # Prevent arbitrary admin assignment unless explicitly chosen
        if role not in ["admin", "operator"]:
            role = "operator"

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if db.get_user_by_username(username):
            flash(f"Username '{username}' is already taken.", "error")
            return render_template("register.html")

        try:
            user = db.create_user(username, email, password, role)
            logger.info("New user registered: username='%s', email='%s', role='%s'", username, email, role)
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            flash(f"Account created successfully as {role}!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            logger.exception("Registration failed for user '%s': %s", username, str(e))
            flash("Registration failed due to a database error.", "error")

    return render_template("register.html")


@app.route("/logout")
def logout():
    """Clears user session and logs out."""
    user = get_current_user()
    if user:
        logger.info("User logged out: username='%s'", user.username)
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# -----------------------------------------------------------------------------
# Main Application Pages
# -----------------------------------------------------------------------------
@app.route("/")
@login_required
def index():
    """Default entry page: redirects or serves dedicated upload page."""
    return render_template("upload.html")


@app.route("/upload")
@login_required
def upload_page():
    """Dedicated single and batch image upload inspection page (separate from camera scan)."""
    return render_template("upload.html")


@app.route("/scan")
@login_required
def scan():
    """Dedicated camera scan page: capture snapshot & analyze (Prompt 12)."""
    return render_template("scan.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """Analytics dashboard page: SQLite metrics & Chart.js charts (Prompt 11)."""
    return render_template("dashboard.html")


@app.route("/live")
@login_required
def live():
    """Browser webcam live continuous inspection stream (Prompt 10)."""
    return render_template("live.html")


@app.route("/ai-scan-view")
@login_required
def ai_scan_view():
    """Multimodal AI Vision scan and model agreement comparison page (Prompt 18 & 19)."""
    return render_template("ai_scan.html")


# -----------------------------------------------------------------------------
# Inspection API Route (Prompts 8, 11, 12, 14, 17)
# -----------------------------------------------------------------------------
@app.route("/analyze", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def analyze():
    """
    POST /analyze:
    Validates uploaded images, runs multi-stage vision pipeline,
    inserts result rows into SQLite inspections table, logs audit event,
    and returns JSON with annotated overlays and metrics.
    """
    user = get_current_user()
    user_id = user.id if user else None
    username = user.username if user else "anonymous"

    if "images" not in request.files and "image" not in request.files and "file" not in request.files:
        logger.warning("Analyze request rejected: No image files provided.")
        return jsonify({"error": "No image files provided in upload request."}), 400

    # Retrieve all files from request
    files: List[Any] = []
    for key in ["images", "image", "file"]:
        if key in request.files:
            files.extend(request.files.getlist(key))

    if not files or all(f.filename == "" for f in files):
        logger.warning("Analyze request rejected: Selected files list is empty.")
        return jsonify({"error": "No selected files."}), 400

    batch_id = str(uuid.uuid4())[:8]
    batch_dir = os.path.join(app.config["UPLOAD_FOLDER"], batch_id)
    os.makedirs(batch_dir, exist_ok=True)

    results: List[Dict[str, Any]] = []

    for file in files:
        if not file or file.filename == "":
            continue

        raw_filename = secure_filename(file.filename) or f"scan_{int(time.time()*1000)}.jpg"
        if not allowed_file(raw_filename):
            logger.warning("Analyze rejected invalid file extension: '%s'", raw_filename)
            return jsonify({
                "error": f"Invalid file format '{raw_filename}'. Allowed formats: .jpg, .png, .bmp"
            }), 400

        save_path = os.path.join(batch_dir, raw_filename)
        file.save(save_path)

        # Validate uncorrupted image (Prompt 14)
        test_img = cv2.imread(save_path)
        if test_img is None or test_img.size == 0:
            logger.warning("Analyze rejected unreadable/corrupted image file: '%s'", raw_filename)
            if os.path.exists(save_path):
                os.remove(save_path)
            return jsonify({
                "error": f"Corrupted or unreadable image file: '{raw_filename}'."
            }), 400

        # Execute run_inspection() pipeline
        try:
            insp = run_inspection(save_path, output_dir=batch_dir, save_annotation=True)

            # Convert annotated BGR image to base64 for direct browser rendering
            annotated_bgr = insp.get("annotated_image_bgr")
            if annotated_bgr is not None:
                _, buffer = cv2.imencode(".jpg", annotated_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
                b64_str = base64.b64encode(buffer).decode("utf-8")
                annotated_b64 = f"data:image/jpeg;base64,{b64_str}"
            else:
                annotated_b64 = ""

            result_item = {
                "filename": raw_filename,
                "is_defective": insp["is_defective"],
                "decision": insp["decision"],
                "defect_type": insp["defect_type"],
                "confidence": insp["confidence"],
                "defect_area": insp["defect_area"],
                "defect_area_mm2": insp["defect_area_mm2"],
                "anomaly_score": insp["anomaly_score"],
                "severity_score": insp["severity_score"],
                "severity_category": insp["severity_category"],
                "recommended_action": insp["recommended_action"],
                "inference_time_ms": insp["inference_time_ms"],
                "bounding_boxes": insp["bounding_boxes"],
                "annotated_image_base64": annotated_b64
            }
            results.append(result_item)

            # Prompt 11 & Prompt 21: Insert row into SQLite inspections table with product_id traceability
            req_product_id = request.form.get("product_id") or request.form.get("batch_id") or None
            insp_id, assigned_pid = db.add_inspection(
                filename=raw_filename,
                is_defective=insp["is_defective"],
                defect_type=insp["defect_type"],
                confidence=insp["confidence"],
                defect_area=insp["defect_area"],
                severity_score=insp["severity_score"],
                severity_category=insp["severity_category"],
                user_id=user_id,
                product_id=req_product_id
            )
            result_item["inspection_id"] = insp_id
            result_item["product_id"] = assigned_pid
            result_item["product_history_url"] = f"/product/{assigned_pid}/history"
            result_item["qr_code_url"] = f"/api/product/{assigned_pid}/qr"

            # Prompt 18: Multimodal AI Vision comparison if enabled via toggle
            enable_ai = (request.form.get("enable_ai_scan") in ["true", "1", "yes"] or
                         request.form.get("ai_scan") in ["true", "1", "yes"])
            if enable_ai:
                ai_prov = request.form.get("provider") or os.environ.get("AI_VISION_PROVIDER", "gemini")
                try:
                    ai_res = analyze_with_ai(save_path, provider=ai_prov)
                    result_item["ai_scan"] = ai_res
                    result_item["agreement"] = (result_item["is_defective"] == ai_res.get("is_defective", False))
                    result_item["provider"] = ai_prov
                except Exception as ex:
                    logger.warning("AI vision scan error in analyze: %s", str(ex))
                    result_item["ai_scan"] = {"error": str(ex), "is_defective": False, "analysis": "Unavailable"}
                    result_item["agreement"] = None
                    result_item["provider"] = ai_prov

            # Prompt 14: Structured Audit Log
            logger.info(
                "[INSPECTION] user=%s filename=%s is_defective=%s type=%s conf=%.3f sev=%.1f (%s) latency=%.1fms",
                username,
                raw_filename,
                insp["is_defective"],
                insp["defect_type"],
                insp["confidence"],
                insp["severity_score"],
                insp["severity_category"],
                insp["inference_time_ms"]
            )

        except Exception as e:
            logger.exception("Error during inspection of '%s': %s", raw_filename, str(e))
            return jsonify({"error": f"Error inspecting '{raw_filename}': {str(e)}"}), 500

    # Write batch CSV report
    csv_filename = f"report_{batch_id}.csv"
    csv_path = os.path.join(REPORTS_FOLDER, csv_filename)
    fieldnames = [
        "filename", "is_defective", "decision", "defect_type", "confidence",
        "defect_area_px", "defect_area_mm2", "anomaly_score",
        "severity_score", "severity_category", "recommended_action", "inference_time_ms"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "filename": r["filename"],
                "is_defective": r["is_defective"],
                "decision": r["decision"],
                "defect_type": r["defect_type"],
                "confidence": f"{r['confidence']:.4f}",
                "defect_area_px": r["defect_area"],
                "defect_area_mm2": r["defect_area_mm2"],
                "anomaly_score": f"{r['anomaly_score']:.4f}",
                "severity_score": r["severity_score"],
                "severity_category": r["severity_category"],
                "recommended_action": r["recommended_action"],
                "inference_time_ms": r["inference_time_ms"]
            })

    BATCH_REPORTS[batch_id] = {
        "csv_path": csv_path,
        "results": results
    }

    return jsonify({
        "batch_id": batch_id,
        "count": len(results),
        "results": results,
        "report_url": f"/report/{batch_id}"
    })


@app.route("/report/<batch_id>")
@login_required
def download_report(batch_id: str):
    """Returns downloadable CSV report file for a specific batch."""
    csv_path = os.path.join(REPORTS_FOLDER, f"report_{batch_id}.csv")
    if os.path.exists(csv_path):
        return send_file(
            csv_path,
            as_attachment=True,
            download_name=f"defect_inspection_report_{batch_id}.csv",
            mimetype="text/csv"
        )

    if batch_id in BATCH_REPORTS and os.path.exists(BATCH_REPORTS[batch_id]["csv_path"]):
        return send_file(
            BATCH_REPORTS[batch_id]["csv_path"],
            as_attachment=True,
            download_name=f"defect_inspection_report_{batch_id}.csv",
            mimetype="text/csv"
        )

    return jsonify({"error": f"Report for batch '{batch_id}' not found."}), 404


# -----------------------------------------------------------------------------
# AI Vision Scan Route (Prompt 18)
# -----------------------------------------------------------------------------
@app.route("/ai-scan", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def ai_scan():
    """
    POST /ai-scan:
    Runs custom-trained ResNet/CAE inspection alongside external multimodal
    AI vision model (Gemini / OpenAI / Claude) on the identical image.
    Returns comparison payload with match agreement indicator and adds row to DB.
    """
    user = get_current_user()
    user_id = user.id if user else None
    username = user.username if user else "anonymous"

    # Check for image file
    file = None
    for key in ["image", "images", "file"]:
        if key in request.files:
            file = request.files[key]
            break

    if not file or file.filename == "":
        return jsonify({"error": "No image file provided for AI Vision scan."}), 400

    raw_filename = secure_filename(file.filename) or f"aiscan_{int(time.time()*1000)}.jpg"
    if not allowed_file(raw_filename):
        return jsonify({"error": f"Invalid format '{raw_filename}'. Allowed: .jpg, .png, .bmp"}), 400

    scan_dir = os.path.join(app.config["UPLOAD_FOLDER"], "ai_scans")
    os.makedirs(scan_dir, exist_ok=True)
    save_path = os.path.join(scan_dir, raw_filename)
    file.save(save_path)

    provider = request.form.get("provider") or os.environ.get("AI_VISION_PROVIDER", "gemini")

    # 1. Run Custom Pipeline
    try:
        insp = run_inspection(save_path, output_dir=scan_dir, save_annotation=True)
        annotated_bgr = insp.get("annotated_image_bgr")
        if annotated_bgr is not None:
            _, buffer = cv2.imencode(".jpg", annotated_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            b64_str = base64.b64encode(buffer).decode("utf-8")
            annotated_b64 = f"data:image/jpeg;base64,{b64_str}"
        else:
            annotated_b64 = ""

        custom_result = {
            "filename": raw_filename,
            "is_defective": insp["is_defective"],
            "decision": insp["decision"],
            "defect_type": insp["defect_type"],
            "confidence": insp["confidence"],
            "defect_area": insp["defect_area"],
            "defect_area_mm2": insp["defect_area_mm2"],
            "anomaly_score": insp["anomaly_score"],
            "severity_score": insp["severity_score"],
            "severity_category": insp["severity_category"],
            "recommended_action": insp["recommended_action"],
            "inference_time_ms": insp["inference_time_ms"],
            "annotated_image_base64": annotated_b64
        }
    except Exception as e:
        logger.exception("Custom model inspection failed during AI scan: %s", str(e))
        return jsonify({"error": f"Custom pipeline error: {str(e)}"}), 500

    # 2. Run Multimodal AI Vision Model
    ai_result = analyze_with_ai(save_path, provider=provider)

    # 3. Assess Agreement
    agreement = (custom_result["is_defective"] == ai_result["is_defective"])

    # 4. Insert row into Database
    req_product_id = request.form.get("product_id") or request.form.get("batch_id") or None
    try:
        insp_id, assigned_pid = db.add_inspection(
            filename=raw_filename,
            is_defective=custom_result["is_defective"],
            defect_type=custom_result["defect_type"],
            confidence=custom_result["confidence"],
            defect_area=custom_result["defect_area"],
            severity_score=custom_result["severity_score"],
            severity_category=custom_result["severity_category"],
            user_id=user_id,
            product_id=req_product_id
        )
    except Exception as e:
        logger.error("Failed to insert inspection into db: %s", str(e))
        insp_id = None
        assigned_pid = req_product_id or f"PROD-{int(time.time())}"

    logger.info(
        "[AI_DUAL_SCAN] user=%s filename=%s custom_def=%s ai_def=%s match=%s provider=%s product=%s",
        username, raw_filename, custom_result["is_defective"], ai_result["is_defective"], agreement, provider, assigned_pid
    )

    return jsonify({
        "status": "success",
        "inspection_id": insp_id,
        "product_id": assigned_pid,
        "product_history_url": f"/product/{assigned_pid}/history",
        "qr_code_url": f"/api/product/{assigned_pid}/qr",
        "provider": provider,
        "agreement": agreement,
        "filename": raw_filename,
        "custom_model": custom_result,
        "ai_model": ai_result
    })


# -----------------------------------------------------------------------------
# PDF Inspection Report Routes (Prompt 20)
# -----------------------------------------------------------------------------
@app.route("/report/pdf/<int:inspection_id>")
@login_required
def download_single_pdf_report(inspection_id: int):
    """
    GET /report/pdf/<inspection_id>:
    Generates and streams single-part PDF inspection QA certificate.
    """
    insp_data = db.get_inspection_by_id(inspection_id)
    if not insp_data:
        return jsonify({"error": f"Inspection #{inspection_id} not found in database."}), 404

    user = get_current_user()
    inspector = user.username if user else insp_data.get("inspector_name", "Automated QA")

    annotated_path = None
    possible_dirs = [
        os.path.join(app.config["UPLOAD_FOLDER"], "ai_scans"),
        app.config["UPLOAD_FOLDER"]
    ]
    for d in possible_dirs:
        cand = os.path.join(d, f"annotated_{insp_data['filename']}")
        if os.path.exists(cand):
            annotated_path = cand
            break
        cand2 = os.path.join(d, insp_data["filename"])
        if os.path.exists(cand2):
            annotated_path = cand2
            break

    try:
        pdf_bytes = generate_pdf_report(
            inspection_id=inspection_id,
            inspection_data=insp_data,
            annotated_img_path=annotated_path,
            inspector_username=inspector
        )
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=inspection_cert_{inspection_id}.pdf"
            }
        )
    except Exception as e:
        logger.exception("Failed generating PDF report for inspection #%d: %s", inspection_id, str(e))
        return jsonify({"error": f"PDF report generation error: {str(e)}"}), 500


@app.route("/report/pdf/batch/<batch_id>")
@login_required
def download_batch_pdf_report(batch_id: str):
    """
    GET /report/pdf/batch/<batch_id>:
    Compiles all inspections from batch upload into a multi-page PDF summary.
    """
    if batch_id not in BATCH_REPORTS:
        return jsonify({"error": f"Batch inspection '{batch_id}' not found."}), 404

    results = BATCH_REPORTS[batch_id].get("results", [])
    try:
        pdf_bytes = generate_batch_pdf_report(batch_id, results)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=batch_inspection_report_{batch_id}.pdf"
            }
        )
    except Exception as e:
        logger.exception("Failed generating batch PDF for batch '%s': %s", batch_id, str(e))
        return jsonify({"error": f"Batch PDF generation error: {str(e)}"}), 500


# -----------------------------------------------------------------------------
# Product Traceability & QR Tracking Routes (Prompt 21)
# -----------------------------------------------------------------------------
@app.route("/product/<product_id>/history")
@login_required
def product_history(product_id: str):
    """
    GET /product/<product_id>/history:
    Renders chronological timeline showing every inspection ever recorded
    for a specific product or batch unit.
    """
    clean_pid = secure_filename(product_id).strip() or product_id.strip()
    inspections = db.get_inspections_by_product_id(clean_pid)
    user = get_current_user()

    return render_template(
        "product_history.html",
        product_id=clean_pid,
        inspections=inspections,
        current_user=user
    )


@app.route("/api/product/<product_id>/history")
@login_required
def api_product_history(product_id: str):
    """
    GET /api/product/<product_id>/history:
    JSON API endpoint returning inspection records and lifecycle metrics for a product.
    """
    clean_pid = secure_filename(product_id).strip() or product_id.strip()
    inspections = db.get_inspections_by_product_id(clean_pid)
    return jsonify({
        "product_id": clean_pid,
        "count": len(inspections),
        "inspections": inspections,
        "qr_code_url": f"/api/product/{clean_pid}/qr"
    })


@app.route("/api/product/<product_id>/qr")
def product_qr_code(product_id: str):
    """
    GET /api/product/<product_id>/qr:
    Generates and streams high-contrast PNG QR Code linking directly to the product's
    traceability timeline for physical product labels and packaging.
    """
    clean_pid = secure_filename(product_id).strip() or product_id.strip()
    target_uri = f"/product/{clean_pid}/history"
    png_bytes = generate_qr_png_bytes(target_uri, box_size=8, border=4)

    headers = {"Content-Type": "image/png"}
    if request.args.get("download") == "1":
        headers["Content-Disposition"] = f"attachment; filename=qr_tag_{clean_pid}.png"

    return Response(png_bytes, mimetype="image/png", headers=headers)


# -----------------------------------------------------------------------------
# In-App Notifications & Alerts API Routes (Prompt 22)
# -----------------------------------------------------------------------------
@app.route("/api/notifications")
@login_required
def get_notifications():
    """
    GET /api/notifications:
    Returns list of recent in-app alerts and current unread count for navbar bell.
    """
    try:
        limit = int(request.args.get("limit", 25))
    except ValueError:
        limit = 25

    notifs = db.get_notifications(limit=limit)
    unread = db.get_unread_notification_count()

    return jsonify({
        "status": "success",
        "unread_count": unread,
        "notifications": notifs
    })


@app.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id: int):
    """
    POST /api/notifications/<id>/read:
    Marks an individual alert as read.
    """
    db.mark_notification_as_read(notification_id)
    return jsonify({"status": "success", "marked_id": notification_id})


@app.route("/api/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """
    POST /api/notifications/read-all:
    Clears all unread notifications.
    """
    db.mark_all_notifications_as_read()
    return jsonify({"status": "success", "message": "All notifications marked as read."})


# -----------------------------------------------------------------------------
# Admin Settings & No-Code Threshold Tuning (Prompt 23)
# -----------------------------------------------------------------------------
@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    """
    GET /admin/settings: Renders threshold configuration panel and audit history.
    POST /admin/settings: Validates and saves updated pipeline parameters in DB.
    """
    user = get_current_user()
    username = user.username if user else "admin"

    if request.method == "POST":
        allowed_keys = [
            "anomaly_threshold",
            "min_defect_area_px",
            "severity_minor_cutoff",
            "severity_major_cutoff",
            "alert_severity_threshold",
            "alert_rate_window_n",
            "alert_rate_threshold_pct",
            "ai_scan_provider",
            "alerts_enabled"
        ]

        updated_count = 0
        for k in allowed_keys:
            if k in request.form:
                val = request.form[k].strip()
                if val:
                    db.update_setting(k, val, changed_by=username)
                    updated_count += 1

        flash(f"Successfully saved {updated_count} pipeline parameters! Changes are active immediately.", "success")
        return redirect(url_for("admin_settings"))

    all_settings = db.get_all_settings()
    history = db.get_settings_history(limit=50)

    return render_template(
        "admin_settings.html",
        settings=all_settings,
        history=history,
        current_user=user
    )


@app.route("/admin/settings/reset", methods=["POST"])
@admin_required
def admin_settings_reset():
    """
    POST /admin/settings/reset:
    Resets all dynamic pipeline settings to factory defaults.
    """
    user = get_current_user()
    username = user.username if user else "admin"
    db.reset_settings_to_defaults(changed_by=username)
    flash("Factory defaults restored for all defect detection thresholds.", "success")
    return redirect(url_for("admin_settings"))



# -----------------------------------------------------------------------------
# Analytics Dashboard API Routes (Prompt 11)
# -----------------------------------------------------------------------------
@app.route("/api/dashboard-data")
@login_required
def dashboard_data():
    """
    GET /api/dashboard-data:
    Supplies JSON data for Chart.js: summary KPIs, defects over time (7/30d),
    defect type distribution, severity breakdown, and filtered recent 20 inspections.
    """
    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        days = 30

    defect_filter = request.args.get("defect_type", "all")
    severity_filter = request.args.get("severity", "all")

    data = db.get_dashboard_metrics(days=days, defect_filter=defect_filter, severity_filter=severity_filter)
    user = get_current_user()
    data["current_user"] = {
        "username": user.username if user else "",
        "role": user.role if user else "operator",
        "is_admin": user.is_admin() if user else False
    }
    return jsonify(data)


@app.route("/clear-history", methods=["POST"])
@admin_required
def clear_history():
    """
    POST /clear-history:
    Wipes the SQLite inspections table.
    Restricted strictly to users with the 'admin' role (Prompt 11, Prompt 13).
    """
    user = get_current_user()
    db.clear_inspections()
    logger.warning("INSPECTION HISTORY CLEARED by admin user: '%s'", user.username if user else "admin")
    return jsonify({
        "status": "success",
        "message": "Inspection history database cleared successfully."
    })


@app.route("/export-csv")
@login_required
def export_csv():
    """
    GET /export-csv:
    Streams all historical inspections from SQLite as a downloadable CSV (Prompt 11).
    """
    records = db.get_all_inspections_for_csv()
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id", "timestamp", "filename", "is_defective", "defect_type",
            "confidence", "defect_area", "severity_score", "severity_category"
        ]
    )
    writer.writeheader()
    for row in records:
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    filename = f"inspections_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# -----------------------------------------------------------------------------
# System Health & Version Checks (Prompt 14 & 17)
# -----------------------------------------------------------------------------
@app.route("/version")
def version_endpoint():
    """
    GET /version:
    Returns detailed semantic versioning, model architectures, and commit information (Prompt 17).
    """
    return jsonify(get_version_info()), 200


@app.route("/api/openapi.json")
def openapi_spec():
    """Returns OpenAPI 3.0.0 Specification for industrial inspection endpoints (Prompt 17)."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Industrial Vision Defect Detection API",
            "version": "1.4.0",
            "description": "Production REST API for automated surface defect detection, multimodal AI verification, and QA reporting."
        },
        "servers": [{"url": "/", "description": "Active Workstation Host"}],
        "paths": {
            "/version": {
                "get": {
                    "summary": "Application & Model Version Metadata",
                    "responses": {"200": {"description": "Version details"}}
                }
            },
            "/health": {
                "get": {
                    "summary": "System Health & Diagnostic Check",
                    "responses": {"200": {"description": "Health status"}}
                }
            },
            "/analyze": {
                "post": {
                    "summary": "Execute Defect Detection Pipeline (Multi-part upload)",
                    "responses": {"200": {"description": "Inspection findings"}}
                }
            },
            "/ai-scan": {
                "post": {
                    "summary": "Dual-Engine Multimodal Inspection & Consensus Verification",
                    "responses": {"200": {"description": "Dual-engine comparison payload"}}
                }
            },
            "/api/dashboard-data": {
                "get": {
                    "summary": "Query Analytics KPIs & Historical Timeline",
                    "responses": {"200": {"description": "Chart.js aggregated metrics"}}
                }
            },
            "/report/pdf/{id}": {
                "get": {
                    "summary": "Download Official Signed Inspection QA Certificate (PDF)",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Binary PDF stream"}}
                }
            },
            "/report/pdf/batch/{batch_id}": {
                "get": {
                    "summary": "Download Multi-Page Batch Inspection Summary (PDF)",
                    "parameters": [{"name": "batch_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Binary PDF stream"}}
                }
            }
        }
    }
    return jsonify(spec), 200


@app.route("/api/docs")
def swagger_ui():
    """Interactive Swagger/OpenAPI UI Explorer (Prompt 17)."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>API Documentation - Vision Defect Inspection</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body { margin: 0; background: #0f172a; }
    .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
    .swagger-ui .topbar { display: none; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: '/api/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis]
      });
    };
  </script>
</body>
</html>"""
    return html, 200, {"Content-Type": "text/html"}


@app.route("/health")
def health():

    """
    GET /health:
    Production health check monitoring application status, deep learning models,
    database connectivity, and disk space for uploads directory.
    """
    try:
        # Check database connectivity
        summary = db.get_dashboard_metrics(days=1)
        db_status = "connected"
        total_records = summary["summary"]["total_inspections"]
    except Exception as e:
        db_status = f"error: {str(e)}"
        total_records = 0

    # Check upload folder disk space
    try:
        disk_usage = shutil.disk_usage(app.config["UPLOAD_FOLDER"])
        total_mb = round(disk_usage.total / (1024 * 1024), 1)
        free_mb = round(disk_usage.free / (1024 * 1024), 1)
        percent_free = round((disk_usage.free / disk_usage.total) * 100, 1)
    except Exception:
        total_mb, free_mb, percent_free = 0.0, 0.0, 0.0

    uptime_sec = round(time.time() - APP_START_TIME, 1)

    health_data = {
        "status": "healthy",
        "app_name": "Inspectra AI",
        "tagline": "Ai powered visual inspection",
        "version": "1.4.0",
        "uptime_seconds": uptime_sec,
        "models": {
            "cae_anomaly_detector": "loaded",
            "resnet_classifier": "loaded",
            "gradcam_engine": "ready",
            "morphological_refinement": "ready",
            "execution_device": "cpu"
        },
        "database": {
            "engine": "SQLite",
            "status": db_status,
            "total_inspections_logged": total_records
        },
        "storage": {
            "uploads_directory": app.config["UPLOAD_FOLDER"],
            "total_mb": total_mb,
            "free_mb": free_mb,
            "percent_free": percent_free
        }
    }

    return jsonify(health_data), 200


# -----------------------------------------------------------------------------
# Global Error Handlers (Prompt 14)
# -----------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request_handler(error):
    msg = getattr(error, "description", "Bad Request")
    if request.is_json or request.path.startswith("/api/") or request.path == "/analyze":
        return jsonify({"error": msg, "code": 400}), 400
    return render_template("error.html", error_code=400, message=msg), 400


@app.errorhandler(401)
def unauthorized_handler(error):
    if request.is_json or request.path.startswith("/api/") or request.path == "/analyze":
        return jsonify({"error": "Unauthorized: Authentication required.", "code": 401}), 401
    return redirect(url_for("login", next=request.url))


@app.errorhandler(403)
def forbidden_handler(error):
    msg = getattr(error, "description", "Access Forbidden")
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": msg, "code": 403}), 403
    return render_template("error.html", error_code=403, message="Access forbidden. Admin role required."), 403


@app.errorhandler(404)
def not_found_handler(error):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found.", "code": 404}), 404
    return render_template("error.html", error_code=404, message="The requested page or endpoint does not exist."), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    logger.warning("Upload rejected: Request entity too large (>10MB).")
    if request.is_json or request.path.startswith("/api/") or request.path == "/analyze":
        return jsonify({"error": "File size exceeds the 10 MB maximum allowed limit.", "code": 413}), 413
    return render_template("error.html", error_code=413, message="File size exceeds the 10 MB maximum allowed limit."), 413


@app.errorhandler(429)
def ratelimit_handler(error):
    logger.warning("Rate limit exceeded on %s by %s", request.path, request.remote_addr)
    return jsonify({
        "error": "Rate limit exceeded. Maximum 20 requests per minute allowed.",
        "code": 429
    }), 429


@app.errorhandler(500)
def internal_server_error(error):
    logger.exception("Internal server error encountered on %s", request.path)
    if request.is_json or request.path.startswith("/api/") or request.path == "/analyze":
        return jsonify({"error": "Internal server processing error. Check server logs.", "code": 500}), 500
    return render_template("error.html", error_code=500, message="An internal server error occurred while processing the request."), 500


# -----------------------------------------------------------------------------
# Server Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 72)
    print("  INSPECTRA AI — AI POWERED VISUAL INSPECTION WORKSTATION")
    print("  Version: 1.4.0 (Production Hardened — Prompts 0 to 20 Complete)")
    print("  Tagline: Ai powered visual inspection")
    print("  Endpoints:")
    print("    - Batch Upload & Inspect:  http://localhost:5000/")
    print("    - Camera Scan (Prompt 12): http://localhost:5000/scan")
    print("    - Multimodal AI (Prompt 18):http://localhost:5000/ai-scan-view")
    print("    - Analytics (Prompt 11):   http://localhost:5000/dashboard")
    print("    - Live Video (Prompt 10):  http://localhost:5000/live")
    print("    - API Documentation:       http://localhost:5000/api/docs")
    print("    - System Version:          http://localhost:5000/version")
    print("    - Health Check (Prompt 14):http://localhost:5000/health")
    print("    - User Login (Prompt 13):  http://localhost:5000/login")
    print("      (Default Admin: admin / admin123 | Operator: operator / operator123)")
    print("=" * 72)
    app.run(host="0.0.0.0", port=5000, debug=False)

