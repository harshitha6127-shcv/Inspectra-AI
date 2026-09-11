"""
tests/test_app_routes.py - Integration Tests for Flask API & Web Routes
=======================================================================
Tests:
- GET /health endpoint returning 200 and system telemetry
- Authentication & route protection (Prompt 13)
- Role-based permissions (Admin vs Operator for /clear-history)
- POST /analyze endpoint validation (reject non-image, process valid fixture)
- GET /api/dashboard-data metrics format (Prompt 11)
"""

import io
import json
import pytest


class TestFlaskRoutesAndHealth:
    """Test suite for Flask endpoints, error handlers, and authentication."""

    def test_health_endpoint_returns_healthy(self, client):
        """GET /health must return 200 with health metadata."""
        resp = client.get("/health")
        assert resp.status_code == 200

        data = json.loads(resp.data)
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "models" in data
        assert "database" in data
        assert data["database"]["status"] == "connected"
        assert "storage" in data

    def test_unauthenticated_protected_route_redirects(self, client):
        """Unauthenticated client accessing /dashboard or /scan should redirect to /login."""
        resp = client.get("/dashboard")
        assert resp.status_code in [302, 401]
        if resp.status_code == 302:
            assert "/login" in resp.headers.get("Location", "")

    def test_unauthenticated_api_returns_401(self, client):
        """Unauthenticated AJAX/JSON request to /api/dashboard-data must return 401."""
        resp = client.get("/api/dashboard-data", headers={"Accept": "application/json"})
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert "error" in data

    def test_authenticated_operator_can_access_dashboard(self, operator_client):
        """Authenticated operator can access /dashboard and /api/dashboard-data."""
        resp_page = operator_client.get("/dashboard")
        assert resp_page.status_code == 200

        resp_api = operator_client.get("/api/dashboard-data")
        assert resp_api.status_code == 200
        data = json.loads(resp_api.data)
        assert "summary" in data
        assert "timeline" in data
        assert "defect_distribution" in data
        assert "severity_breakdown" in data
        assert "recent_inspections" in data

    def test_operator_cannot_clear_history_forbidden(self, operator_client):
        """Operator attempting to call POST /clear-history must receive 403 Forbidden."""
        resp = operator_client.post("/clear-history")
        assert resp.status_code == 403
        data = json.loads(resp.data)
        assert "Forbidden" in data.get("error", "")

    def test_admin_can_clear_history_success(self, admin_client):
        """Admin calling POST /clear-history must succeed with 200 OK."""
        resp = admin_client.post("/clear-history")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "success"

    def test_analyze_rejects_empty_request(self, operator_client):
        """POST /analyze without files returns 400 Bad Request."""
        resp = operator_client.post("/analyze", data={})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_analyze_rejects_non_image_file(self, operator_client):
        """POST /analyze with a .txt file returns 400 Bad Request."""
        data = {
            "image": (io.BytesIO(b"Not an image"), "notes.txt")
        }
        resp = operator_client.post("/analyze", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        res_json = json.loads(resp.data)
        assert "Invalid file format" in res_json.get("error", "")

    def test_analyze_accepts_valid_image(self, operator_client, normal_image_path):
        """POST /analyze with a valid PNG image executes pipeline and returns JSON."""
        with open(normal_image_path, "rb") as f:
            img_bytes = f.read()

        data = {
            "image": (io.BytesIO(img_bytes), "test_part.png")
        }
        resp = operator_client.post("/analyze", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        res_json = json.loads(resp.data)
        assert "batch_id" in res_json
        assert "results" in res_json
        assert len(res_json["results"]) == 1
        result = res_json["results"][0]
        assert result["filename"] == "test_part.png"
        assert "severity_score" in result
        assert "severity_category" in result
