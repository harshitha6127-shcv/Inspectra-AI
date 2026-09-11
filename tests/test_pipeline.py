"""
tests/test_pipeline.py - Integration Tests for End-to-End Inspection Pipeline
=============================================================================
Tests:
- Complete run_inspection() execution on normal and defective fixtures
- Presence and data types of all required contract keys
- Numerical range validation (confidence, severity score, area, latency)
"""

import os
import pytest
from pipeline import run_inspection


class TestInspectionPipelineIntegration:
    """Integration test suite for the multi-stage vision pipeline."""

    REQUIRED_KEYS = [
        "is_defective",
        "decision",
        "defect_type",
        "confidence",
        "defect_area",
        "defect_area_mm2",
        "anomaly_score",
        "severity_score",
        "severity_category",
        "recommended_action",
        "inference_time_ms",
        "bounding_boxes"
    ]

    def test_run_inspection_on_normal_fixture(self, normal_image_path):
        """Pipeline must inspect normal fixture and return valid conforming report."""
        assert os.path.exists(normal_image_path), f"Missing fixture at {normal_image_path}"

        result = run_inspection(normal_image_path, save_annotation=False)

        # 1. Contract verification: all required keys must exist
        for key in self.REQUIRED_KEYS:
            assert key in result, f"Result dictionary missing contract key: '{key}'"

        # 2. Type verification
        assert isinstance(result["is_defective"], bool)
        assert result["decision"] in ["PASS", "DEFECT"]
        assert isinstance(result["defect_type"], str)
        assert isinstance(result["confidence"], (float, int))
        assert isinstance(result["severity_score"], (float, int))
        assert result["severity_category"] in ["None", "Minor", "Major", "Critical"]
        assert isinstance(result["inference_time_ms"], (float, int))
        assert isinstance(result["bounding_boxes"], list)

        # 3. Value bounds verification
        assert 0.0 <= result["confidence"] <= 1.0
        assert 0.0 <= result["severity_score"] <= 100.0
        assert result["inference_time_ms"] >= 0.0

    def test_run_inspection_on_defective_fixture(self, defective_image_path):
        """Pipeline must inspect synthetic defective fixture and produce defect telemetry."""
        assert os.path.exists(defective_image_path), f"Missing fixture at {defective_image_path}"

        result = run_inspection(defective_image_path, save_annotation=False)

        for key in self.REQUIRED_KEYS:
            assert key in result, f"Result dictionary missing key: '{key}'"

        assert 0.0 <= result["confidence"] <= 1.0
        assert 0.0 <= result["severity_score"] <= 100.0
        assert result["severity_category"] in ["Minor", "Major", "Critical", "None"]
        assert len(result["recommended_action"]) > 0

    def test_run_inspection_missing_file_raises_error(self):
        """Pipeline must raise FileNotFoundError when provided non-existent path."""
        with pytest.raises(FileNotFoundError):
            run_inspection("/non/existent/path/imaginary_part.png")
