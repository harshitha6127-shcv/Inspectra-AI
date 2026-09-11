"""
preprocessing.py - Industrial Preprocessing & Lighting Normalization Pipeline
=============================================================================
Provides robust image conditioning for vision-based defect inspection:
1. Aspect-ratio preserving resize and padding (letterboxing).
2. Lighting normalization via CLAHE on L-channel in CIE LAB color space.
3. Edge-preserving bilateral filter denoising.
4. Orientation and illumination augmentation via Albumentations.
5. Edge-based / thresholding ROI product extraction to eliminate background noise.
6. Matplotlib multi-stage visualization function for side-by-side verification.
"""

import os
from typing import Tuple, Optional, Dict, Any, List
import numpy as np
import cv2

try:
    import albumentations as A
except ImportError:
    A = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def resize_and_pad(
    image: np.ndarray,
    target_size: Tuple[int, int] = (256, 256),
    pad_color: Tuple[int, int, int] = (0, 0, 0)
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Resizes an image while strictly preserving its original aspect ratio,
    padding the remaining dimensions symmetrically with a constant color.

    Args:
        image: Input BGR image of shape (H, W, C) or grayscale (H, W).
        target_size: Target (width, height) tuple.
        pad_color: Padding border color for BGR images (default black).

    Returns:
        padded_img: Image resized and padded to target_size.
        meta: Metadata dictionary containing scale ratio and padding offsets.
    """
    target_w, target_h = target_size
    h, w = image.shape[:2]

    # Compute scale factor to fit inside target bounding box
    scale = min(target_w / w, target_h / h)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))

    # Resize using INTER_AREA for downsampling or INTER_LINEAR for upsampling
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)

    # Calculate symmetric padding margins
    pad_top = (target_h - new_h) // 2
    pad_bottom = target_h - new_h - pad_top
    pad_left = (target_w - new_w) // 2
    pad_right = target_w - new_w - pad_left

    if len(image.shape) == 3:
        padded_img = cv2.copyMakeBorder(
            resized,
            pad_top, pad_bottom, pad_left, pad_right,
            borderType=cv2.BORDER_CONSTANT,
            value=pad_color
        )
    else:
        padded_img = cv2.copyMakeBorder(
            resized,
            pad_top, pad_bottom, pad_left, pad_right,
            borderType=cv2.BORDER_CONSTANT,
            value=pad_color[0]
        )

    meta = {
        "scale": scale,
        "new_shape": (new_h, new_w),
        "pad_top": pad_top,
        "pad_bottom": pad_bottom,
        "pad_left": pad_left,
        "pad_right": pad_right,
        "original_shape": (h, w)
    }
    return padded_img, meta


def apply_clahe_lab(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8)
) -> np.ndarray:
    """
    Normalizes lighting variation, shadows, and non-uniform factory illumination
    using Contrast Limited Adaptive Histogram Equalization (CLAHE) on the
    Luminance (L) channel in CIE LAB color space.
    
    This enhances local defect contrast without amplifying global color saturation
    or causing clipping artifacts.

    Args:
        image: Input BGR image (uint8, [H, W, 3]).
        clip_limit: Threshold for contrast limiting. Higher values increase contrast.
        tile_grid_size: Size of local grid for histogram equalization.

    Returns:
        np.ndarray: Equalized BGR image.
    """
    if len(image.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(image)

    # Convert BGR to CIE LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Apply CLAHE strictly to the L (luminance) channel
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    cl = clahe.apply(l_channel)

    # Merge channels back and convert to BGR
    merged_lab = cv2.merge([cl, a_channel, b_channel])
    equalized_bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
    return equalized_bgr


def denoise_bilateral(
    image: np.ndarray,
    d: int = 7,
    sigma_color: float = 40.0,
    sigma_space: float = 40.0
) -> np.ndarray:
    """
    Lightweight edge-preserving denoising filter.
    Smooths high-frequency sensor noise while preserving sharp boundaries
    of fine hairline cracks, scratches, and machining edges.

    Args:
        image: Input BGR image.
        d: Diameter of each pixel neighborhood.
        sigma_color: Filter sigma in the color space (larger = wider color blending).
        sigma_space: Filter sigma in the coordinate space (larger = farther pixels mix).

    Returns:
        np.ndarray: Denoised image.
    """
    return cv2.bilateralFilter(image, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)


def extract_product_roi(
    image: np.ndarray,
    padding: int = 8,
    min_area_ratio: float = 0.05
) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """
    Detects the product boundary and crops to its Region of Interest (ROI),
    removing conveyor belts, fixtures, or background clutter.

    Args:
        image: Input BGR image.
        padding: Safety pixel margin around detected bounding box.
        min_area_ratio: Minimum fraction of total image area to count as product.

    Returns:
        roi_img: Cropped image focusing on product.
        bbox: (x, y, w, h) bounding box coordinates in original image space.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    # Otsu thresholding + gradient edge detection
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Invert if background is bright
    border_sample = np.concatenate([
        thresh[0, :], thresh[-1, :], thresh[:, 0], thresh[:, -1]
    ])
    if np.mean(border_sample) > 127:
        thresh = cv2.bitwise_not(thresh)

    # Morphological close to bridge internal component gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image, (0, 0, w, h)

    # Find largest contour representing the manufactured part
    largest_c = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest_c)

    if area < (h * w * min_area_ratio):
        # ROI detection fell below threshold; keep original frame
        return image, (0, 0, w, h)

    bx, by, bw, bh = cv2.boundingRect(largest_c)
    x1 = max(0, bx - padding)
    y1 = max(0, by - padding)
    x2 = min(w, bx + bw + padding)
    y2 = min(h, by + bh + padding)

    roi_img = image[y1:y2, x1:x2]
    return roi_img, (x1, y1, x2 - x1, y2 - y1)


def get_orientation_augmentation_pipeline(
    img_size: Tuple[int, int] = (256, 256),
    is_training: bool = True
) -> Any:
    """
    Builds an Albumentations transform pipeline handling rotation, flip,
    and lighting variations for industrial inspection models.
    """
    if A is None:
        return None

    if not is_training:
        return A.Compose([
            A.Resize(height=img_size[1], width=img_size[0]),
        ])

    return A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.5),
        A.RandomRotate90(p=0.5),
        A.ShiftScaleRotate(
            shift_limit=0.05,
            scale_limit=0.08,
            rotate_limit=15,
            border_mode=cv2.BORDER_REFLECT_101,
            p=0.5
        ),
        A.RandomBrightnessContrast(
            brightness_limit=0.15,
            contrast_limit=0.2,
            p=0.4
        ),
        A.HueSaturationValue(
            hue_shift_limit=8,
            sat_shift_limit=15,
            val_shift_limit=15,
            p=0.3
        ),
        A.Resize(height=img_size[1], width=img_size[0])
    ])


def preprocess_image(
    image: np.ndarray,
    target_size: Tuple[int, int] = (256, 256),
    apply_roi: bool = True,
    apply_clahe: bool = True,
    apply_denoise: bool = True,
    clip_limit: float = 2.0
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Full preprocessing pipeline execution for a single manufacturing image.

    Pipeline:
    Raw Image -> ROI Cropping -> CLAHE (LAB) -> Bilateral Denoise -> Resize & Pad

    Returns:
        processed_img: Conditioned image of shape (*target_size[::-1], 3)
        intermediates: Dictionary storing intermediate stage images for auditing.
    """
    intermediates: Dict[str, Any] = {"original": image.copy()}

    # 1. ROI extraction
    if apply_roi:
        roi, bbox = extract_product_roi(image)
        intermediates["roi"] = roi
        intermediates["bbox"] = bbox
        current = roi
    else:
        current = image

    # 2. Lighting normalization via CLAHE on L-channel
    if apply_clahe:
        clahe_img = apply_clahe_lab(current, clip_limit=clip_limit)
        intermediates["clahe"] = clahe_img
        current = clahe_img

    # 3. Bilateral filter edge-preserving smoothing
    if apply_denoise:
        denoised = denoise_bilateral(current, d=7, sigma_color=35.0, sigma_space=35.0)
        intermediates["denoised"] = denoised
        current = denoised

    # 4. Aspect-ratio preserving resize & symmetric padding
    final_img, pad_meta = resize_and_pad(current, target_size=target_size)
    intermediates["final"] = final_img
    intermediates["pad_meta"] = pad_meta

    return final_img, intermediates


def visualize_preprocessing_comparison(
    samples: List[Tuple[str, np.ndarray]],
    save_path: Optional[str] = "outputs/preprocessing_comparison.png",
    show: bool = False
):
    """
    Generates a high-resolution multi-column comparison of inspection stages
    (Original, CLAHE L-Channel, Bilateral Filter, Final Letterboxed).
    """
    if plt is None:
        print("[!] Matplotlib not installed; skipping graphic plot.")
        return

    n_samples = len(samples)
    fig, axes = plt.subplots(n_samples, 4, figsize=(16, 4 * n_samples))
    if n_samples == 1:
        axes = np.expand_dims(axes, 0)

    stages = ["Original Input", "CLAHE (LAB)", "Bilateral Denoise", "Final Preprocessed"]

    for row_idx, (title, img_bgr) in enumerate(samples):
        final_img, inter = preprocess_image(img_bgr)

        imgs_to_show = [
            cv2.cvtColor(inter["original"], cv2.COLOR_BGR2RGB),
            cv2.cvtColor(inter.get("clahe", inter["original"]), cv2.COLOR_BGR2RGB),
            cv2.cvtColor(inter.get("denoised", inter["original"]), cv2.COLOR_BGR2RGB),
            cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB),
        ]

        for col_idx, (stage_name, show_img) in enumerate(zip(stages, imgs_to_show)):
            ax = axes[row_idx, col_idx]
            ax.imshow(show_img)
            ax.set_title(f"{title}\n{stage_name}" if col_idx == 0 else stage_name, fontsize=10)
            ax.axis("off")

    plt.tight_layout()
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[+] Saved preprocessing comparison visualization to {save_path}")
    if show:
        plt.show()
    plt.close()


if __name__ == "__main__":
    print("Running Preprocessing Pipeline verification on sample synthetic defects...")
    from dataset import create_base_texture, inject_crack, inject_scratch, inject_dent

    base = create_base_texture(300, 300, "brushed_metal")
    crack_img, _ = inject_crack(base)
    scratch_img, _ = inject_scratch(base)
    dent_img, _ = inject_dent(base)

    sample_batch = [
        ("Hairline Crack", crack_img),
        ("Surface Scratch", scratch_img),
        ("Localized Dent", dent_img),
    ]

    for name, img in sample_batch:
        proc, inter = preprocess_image(img, target_size=(256, 256))
        print(f"  Processed '{name}': Input {img.shape} -> Output {proc.shape}")

    visualize_preprocessing_comparison(sample_batch, save_path="outputs/preprocessing_comparison.png")
    print("[+] Preprocessing pipeline verification complete.")
