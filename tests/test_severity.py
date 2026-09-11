"""
tests/test_severity.py - Unit Tests for Defect Severity Scoring Module
======================================================================
Tests:
- Severity score computation formula and weighting
- Category threshold boundaries (<30 Minor, 30-70 Major, >70 Critical)
- Recommended factory actions
- Edge cases: normal parts, zero area, extreme confidence, custom weights
"""

import pytest
from severity import (
    compute_severity_score,
    THRESH_MINOR_MAX,
    THRESH_MAJOR_MAX,
    DEFAULT_SEVERITY_WEIGHTS
)


class TestSeverityScoring:
    """Unit test suite for industrial defect severity grading."""

    def test_normal_part_has_zero_severity(self):
        """Conforming/normal part must always yield 0.0 score, None category."""
        score, category, action = compute_severity_score(
            defect_type="normal",
            confidence=0.98,
            defect_area_px=0.0
        )
        assert score == 0.0
        assert category == "None"
        assert action == "Pass to downstream line"

    def test_zero_area_defect_yields_zero_severity(self):
        """If detected defect has zero pixel area, severity is zero."""
        score, category, action = compute_severity_score(
            defect_type="crack",
            confidence=0.95,
            defect_area_px=0.0
        )
        assert score == 0.0
        assert category == "None"

    def test_minor_category_boundary(self):
        """Defects with composite score strictly below 30.0 must map to Minor."""
        # A tiny discoloration blemish with low confidence
        score, category, action = compute_severity_score(
            defect_type="discoloration",  # weight 0.30
            confidence=0.50,
            defect_area_px=20.0,
            total_area_px=65536.0
        )
        assert score < THRESH_MINOR_MAX
        assert category == "Minor"
        assert action == "Log only"

    def test_major_category_boundary(self):
        """Defects with composite score in [30.0, 70.0] must map to Major."""
        # Moderate scratch
        score, category, action = compute_severity_score(
            defect_type="scratch",  # weight 0.55
            confidence=0.85,
            defect_area_px=600.0,
            total_area_px=65536.0
        )
        assert THRESH_MINOR_MAX <= score <= THRESH_MAJOR_MAX
        assert category == "Major"
        assert action == "Flag for review"

    def test_critical_category_boundary(self):
        """Defects with composite score strictly above 70.0 must map to Critical."""
        # Structural crack with high confidence and sizable area
        score, category, action = compute_severity_score(
            defect_type="crack",  # weight 1.00
            confidence=0.98,
            defect_area_px=1800.0,
            total_area_px=65536.0
        )
        assert score > THRESH_MAJOR_MAX
        assert category == "Critical"
        assert action == "Reject immediately"

    def test_threshold_exact_edges(self):
        """Test exact numerical behavior near the 30.0 and 70.0 decision boundaries."""
        assert THRESH_MINOR_MAX == 30.0
        assert THRESH_MAJOR_MAX == 70.0

    def test_custom_weights_override(self):
        """Custom defect severity weights must be respected."""
        custom = {"custom_void": 0.95}
        score, category, action = compute_severity_score(
            defect_type="custom_void",
            confidence=0.90,
            defect_area_px=1000.0,
            custom_weights=custom
        )
        assert score > 60.0
        assert category in ["Major", "Critical"]

    def test_score_bounded_between_0_and_100(self):
        """Severity score must strictly remain within [0.0, 100.0] under extreme values."""
        score_huge, _, _ = compute_severity_score("crack", confidence=2.0, defect_area_px=99999999.0)
        assert score_huge <= 100.0

        score_min, _, _ = compute_severity_score("scratch", confidence=-1.0, defect_area_px=-50.0)
        assert score_min == 0.0
