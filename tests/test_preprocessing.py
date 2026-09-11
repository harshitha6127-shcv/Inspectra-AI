"""
tests/test_preprocessing.py - Unit Tests for Industrial Preprocessing Module
=============================================================================
Tests:
- CLAHE lighting normalization in CIE LAB color space
- Aspect ratio preserving resize and padding
- Edge-case image handling (all-black, all-white, uniform gray)
- Bilateral filter denoising
"""

import numpy as np
import pytest

from preprocessing import (
    apply_clahe_lab,
    resize_and_pad,
    denoise_bilateral,
    extract_product_roi
)


class TestCLAHEPreprocessing:
    """Unit tests for CLAHE contrast and lighting equalization."""

    def test_clahe_output_dimensions_and_type(self):
        """CLAHE must preserve exact (H, W, C) shape and uint8 dtype."""
        img = np.random.randint(0, 256, (120, 160, 3), dtype=np.uint8)
        equalized = apply_clahe_lab(img, clip_limit=2.0, tile_grid_size=(8, 8))

        assert equalized.shape == img.shape
        assert equalized.dtype == np.uint8

    def test_clahe_all_black_image(self):
        """Edge case: All-black image (zeros) must not crash or produce NaNs."""
        black_img = np.zeros((100, 100, 3), dtype=np.uint8)
        result = apply_clahe_lab(black_img)

        assert result.shape == (100, 100, 3)
        assert result.dtype == np.uint8
        assert not np.isnan(result).any()
        # All-black image remains black
        assert np.max(result) == 0

    def test_clahe_all_white_image(self):
        """Edge case: All-white image (255s) must not overflow or crash."""
        white_img = np.full((100, 100, 3), 255, dtype=np.uint8)
        result = apply_clahe_lab(white_img)

        assert result.shape == (100, 100, 3)
        assert result.dtype == np.uint8
        assert not np.isnan(result).any()

    def test_clahe_uniform_gray_image(self):
        """Edge case: Flat uniform gray must preserve uniformity without NaN artifacts."""
        gray_img = np.full((80, 80, 3), 128, dtype=np.uint8)
        result = apply_clahe_lab(gray_img)

        assert result.shape == (80, 80, 3)
        assert result.dtype == np.uint8
        assert not np.isnan(result).any()


class TestResizeAndPad:
    """Unit tests for aspect-ratio preserving letterboxing."""

    def test_resize_and_pad_aspect_ratio_preservation(self):
        """Aspect ratio must be preserved with symmetric padding."""
        # Non-square widescreen aspect ratio: 400x200 (2:1)
        wide_img = np.full((200, 400, 3), 100, dtype=np.uint8)
        target_size = (256, 256)
        padded, meta = resize_and_pad(wide_img, target_size=target_size)

        assert padded.shape == (256, 256, 3)
        assert padded.dtype == np.uint8

        # For 400x200 scaled to 256x256, scale is 256/400 = 0.64
        # New height = round(200 * 0.64) = 128
        # Top padding = (256 - 128) // 2 = 64
        # Bottom padding = 256 - 128 - 64 = 64
        assert meta["scale"] == 0.64
        assert meta["new_shape"] == (128, 256)
        assert meta["pad_top"] == 64
        assert meta["pad_bottom"] == 64
        assert meta["pad_left"] == 0
        assert meta["pad_right"] == 0

    def test_resize_and_pad_tall_image(self):
        """Tall portrait image must pad left and right symmetrically."""
        tall_img = np.full((400, 200, 3), 100, dtype=np.uint8)
        target_size = (256, 256)
        padded, meta = resize_and_pad(tall_img, target_size=target_size)

        assert padded.shape == (256, 256, 3)
        assert meta["pad_left"] == 64
        assert meta["pad_right"] == 64
        assert meta["pad_top"] == 0
        assert meta["pad_bottom"] == 0


class TestDenoiseAndROI:
    """Unit tests for noise filtering and ROI boundary detection."""

    def test_bilateral_filter(self):
        """Bilateral filter must return same shape and uint8 type."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        denoised = denoise_bilateral(img, d=5, sigma_color=30.0, sigma_space=30.0)

        assert denoised.shape == img.shape
        assert denoised.dtype == np.uint8

    def test_extract_product_roi_returns_bbox(self):
        """ROI extraction must return valid cropped image and bounding box."""
        canvas = np.zeros((200, 200, 3), dtype=np.uint8)
        # Add a bright object in center
        canvas[50:150, 50:150] = 200
        roi, bbox = extract_product_roi(canvas, padding=4)

        assert roi.size > 0
        x, y, w, h = bbox
        assert x >= 0 and y >= 0 and w > 0 and h > 0
