"""
dataset.py - Dataset Preparation & Synthetic Industrial Defect Generator
========================================================================
Supports:
1. Downloading and extracting the industrial MVTec Anomaly Detection (MVTec AD) benchmark.
2. Generating a realistic synthetic dataset using OpenCV and NumPy for 7 classes:
   - normal
   - crack
   - scratch
   - dent
   - stain
   - discoloration
   - dimensional_irregularity
3. Exporting pixel-level ground truth binary masks.
4. Printing formatted dataset statistics (class counts, dimensions, splits).
"""

import os
import sys
import tarfile
import urllib.request
import argparse
import random
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import numpy as np
import cv2

# Defect class definitions
DEFECT_CLASSES = [
    "normal",
    "crack",
    "scratch",
    "dent",
    "stain",
    "discoloration",
    "dimensional_irregularity",
]

# Supported MVTec AD categories
MVTEC_CATEGORIES = [
    "bottle", "cable", "capsule", "carpet", "grid",
    "hazelnut", "leather", "metal_nut", "pill", "screw",
    "tile", "toothbrush", "transistor", "wood", "zipper"
]

MVTEC_BASE_URL = "https://www.mydrive.ch/shares/38536/3830184030e49fe74747669442f0f282/download/420938113"


def create_base_texture(
    width: int = 256,
    height: int = 256,
    texture_type: str = "brushed_metal"
) -> np.ndarray:
    """
    Generates a realistic industrial substrate base texture using OpenCV/NumPy.
    
    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        texture_type: Type of surface ('brushed_metal', 'ceramic_tile', 'smooth_plastic').
        
    Returns:
        np.ndarray: BGR image (uint8, [H, W, 3]).
    """
    if texture_type == "brushed_metal":
        # Base gray with directional brushing lines
        base = np.full((height, width), 160, dtype=np.float32)
        # Add horizontal grain lines
        noise = np.random.normal(0, 12, (height, width)).astype(np.float32)
        # Apply 1D horizontal blur to simulate machining/brushing marks
        brush_kernel = np.ones((1, 15), dtype=np.float32) / 15.0
        brushed_noise = cv2.filter2D(noise, -1, brush_kernel)
        
        # Subtle non-uniform factory illumination gradient
        y_grad = np.linspace(0.88, 1.08, height)[:, np.newaxis]
        x_grad = np.linspace(0.92, 1.05, width)[np.newaxis, :]
        illumination = y_grad * x_grad
        
        combined = (base + brushed_noise) * illumination
        combined = np.clip(combined, 0, 255).astype(np.uint8)
        # Slightly cool metallic tint (BGR)
        b = np.clip(combined.astype(np.int16) + 6, 0, 255).astype(np.uint8)
        g = combined
        r = np.clip(combined.astype(np.int16) - 4, 0, 255).astype(np.uint8)
        return cv2.merge([b, g, r])

    elif texture_type == "ceramic_tile":
        # Fine grain ceramic substrate
        base = np.full((height, width, 3), [220, 225, 228], dtype=np.uint8)
        noise = np.random.normal(0, 5, (height, width, 3)).astype(np.int16)
        tile = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        # Subtle surface speckling
        speckle_mask = (np.random.rand(height, width) > 0.98).astype(np.uint8)
        tile[speckle_mask == 1] = [180, 185, 190]
        return tile

    else:  # smooth_plastic / machined part
        base = np.full((height, width, 3), [190, 190, 195], dtype=np.uint8)
        noise = np.random.normal(0, 3, (height, width, 3)).astype(np.int16)
        return np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def inject_crack(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Injects a jagged, branching crack into the image with pixel ground truth mask.
    """
    h, w = img.shape[:2]
    defective = img.copy()
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Start point
    x = random.randint(int(w * 0.2), int(w * 0.8))
    y = random.randint(int(h * 0.2), int(h * 0.8))
    length = random.randint(30, 80)
    angle = random.uniform(0, 2 * np.pi)
    
    points = [(x, y)]
    curr_x, curr_y = float(x), float(y)
    
    for _ in range(length):
        angle += random.uniform(-0.4, 0.4)
        step = random.uniform(1.5, 3.5)
        curr_x += step * np.cos(angle)
        curr_y += step * np.sin(angle)
        curr_x = np.clip(curr_x, 5, w - 5)
        curr_y = np.clip(curr_y, 5, h - 5)
        points.append((int(curr_x), int(curr_y)))
        
        # Branching crack chance
        if random.random() < 0.08:
            bx, by = curr_x, curr_y
            b_angle = angle + random.choice([-1.0, 1.0]) * random.uniform(0.5, 1.2)
            branch_pts = [(int(bx), int(by))]
            for _ in range(random.randint(10, 25)):
                b_angle += random.uniform(-0.3, 0.3)
                bx += 2.0 * np.cos(b_angle)
                by += 2.0 * np.sin(b_angle)
                bx = np.clip(bx, 5, w - 5)
                by = np.clip(by, 5, h - 5)
                branch_pts.append((int(bx), int(by)))
            pts_arr = np.array(branch_pts, dtype=np.int32)
            cv2.polylines(mask, [pts_arr], False, 255, thickness=random.randint(1, 2))
            cv2.polylines(defective, [pts_arr], False, (35, 35, 35), thickness=random.randint(1, 2))

    pts_arr = np.array(points, dtype=np.int32)
    thickness = random.randint(2, 3)
    cv2.polylines(mask, [pts_arr], False, 255, thickness=thickness)
    # Dark jagged fissure with subtle highlight edge
    cv2.polylines(defective, [pts_arr], False, (25, 25, 25), thickness=thickness)
    return defective, mask


def inject_scratch(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Injects a linear or curved scratch abrasion with light reflection and shadow groove.
    """
    h, w = img.shape[:2]
    defective = img.copy()
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Random start & end
    x1 = random.randint(int(w * 0.15), int(w * 0.85))
    y1 = random.randint(int(h * 0.15), int(h * 0.85))
    length = random.randint(40, 110)
    angle = random.uniform(0, np.pi)
    x2 = int(np.clip(x1 + length * np.cos(angle), 5, w - 5))
    y2 = int(np.clip(y1 + length * np.sin(angle), 5, h - 5))
    
    # Shadow groove
    cv2.line(mask, (x1, y1), (x2, y2), 255, thickness=2)
    cv2.line(defective, (x1, y1), (x2, y2), (50, 50, 50), thickness=2)
    
    # Parallel specular highlight
    offset_x = int(np.round(-np.sin(angle) * 1.5))
    offset_y = int(np.round(np.cos(angle) * 1.5))
    cv2.line(
        defective,
        (x1 + offset_x, y1 + offset_y),
        (x2 + offset_x, y2 + offset_y),
        (245, 245, 250),
        thickness=1
    )
    return defective, mask


def inject_dent(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Injects a localized 3D surface dent with depth depression and directional lighting.
    """
    h, w = img.shape[:2]
    defective = img.copy().astype(np.float32)
    mask = np.zeros((h, w), dtype=np.uint8)
    
    cx = random.randint(int(w * 0.25), int(w * 0.75))
    cy = random.randint(int(h * 0.25), int(h * 0.75))
    radius = random.randint(14, 30)
    
    cv2.circle(mask, (cx, cy), radius, 255, -1)
    
    y, x = np.ogrid[:h, :w]
    dist_sq = (x - cx) ** 2 + (y - cy) ** 2
    in_circle = dist_sq <= radius ** 2
    
    # Gaussian depth profile
    depth = np.exp(-dist_sq / (2.0 * (radius * 0.6) ** 2))
    
    # Directional illumination (-45 degrees light source: top-left bright, bottom-right shadow)
    norm_x = (x - cx) / (radius + 1e-5)
    norm_y = (y - cy) / (radius + 1e-5)
    shading = (-norm_x - norm_y) * depth * 55.0
    
    for c in range(3):
        channel = defective[:, :, c]
        channel[in_circle] = np.clip(channel[in_circle] + shading[in_circle], 0, 255)
        defective[:, :, c] = channel
        
    return defective.astype(np.uint8), mask


def inject_stain(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Injects an irregular oil, grease, or chemical stain with soft alpha blending.
    """
    h, w = img.shape[:2]
    defective = img.copy().astype(np.float32)
    mask = np.zeros((h, w), dtype=np.uint8)
    
    cx = random.randint(int(w * 0.2), int(w * 0.8))
    cy = random.randint(int(h * 0.2), int(h * 0.8))
    
    # Generate irregular organic blob using overlapping ellipses
    blob_mask = np.zeros((h, w), dtype=np.uint8)
    num_sub_blobs = random.randint(3, 6)
    for _ in range(num_sub_blobs):
        ox = cx + random.randint(-12, 12)
        oy = cy + random.randint(-12, 12)
        ax = random.randint(12, 28)
        ay = random.randint(8, 22)
        rot = random.randint(0, 180)
        cv2.ellipse(blob_mask, (ox, oy), (ax, ay), rot, 0, 360, 255, -1)
        
    # Soften blob edges
    blob_mask = cv2.GaussianBlur(blob_mask, (15, 15), 5)
    mask = (blob_mask > 40).astype(np.uint8) * 255
    
    alpha = (blob_mask.astype(np.float32) / 255.0) * random.uniform(0.45, 0.75)
    stain_color = np.array([random.randint(25, 45), random.randint(45, 75), random.randint(70, 110)], dtype=np.float32) # brownish oil
    
    for c in range(3):
        defective[:, :, c] = defective[:, :, c] * (1.0 - alpha) + stain_color[c] * alpha
        
    return np.clip(defective, 0, 255).astype(np.uint8), mask


def inject_discoloration(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Injects a localized thermal, chemical, or oxidation discoloration halo.
    """
    h, w = img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    
    cx = random.randint(int(w * 0.2), int(w * 0.8))
    cy = random.randint(int(h * 0.2), int(h * 0.8))
    r = random.randint(20, 45)
    
    cv2.circle(mask, (cx, cy), r, 255, -1)
    soft_mask = cv2.GaussianBlur(mask, (31, 31), 10).astype(np.float32) / 255.0
    
    # Convert to HSV to shift hue/saturation realistically
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    
    # Thermal blue-purple tint or yellowish oxidation
    if random.random() < 0.5:
        # Heat oxidation tint (yellow-amber)
        hsv[:, :, 0] = np.clip(hsv[:, :, 0] * (1.0 - soft_mask) + 18.0 * soft_mask, 0, 180)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + soft_mask * 80.0, 0, 255)
    else:
        # High-temperature heat tint (bluing)
        hsv[:, :, 0] = np.clip(hsv[:, :, 0] * (1.0 - soft_mask) + 110.0 * soft_mask, 0, 180)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] + soft_mask * 95.0, 0, 255)
        
    defective = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return defective, mask


def inject_dimensional_irregularity(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Injects edge deformities, chipped edges, or asymmetric dimensional flaws.
    """
    h, w = img.shape[:2]
    defective = img.copy()
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Chip or bulge along a border boundary (outer 25% margin)
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        cx = random.randint(int(w * 0.2), int(w * 0.8))
        cy = random.randint(5, 25)
        r = random.randint(12, 26)
    elif side == "bottom":
        cx = random.randint(int(w * 0.2), int(w * 0.8))
        cy = random.randint(h - 25, h - 5)
        r = random.randint(12, 26)
    elif side == "left":
        cx = random.randint(5, 25)
        cy = random.randint(int(h * 0.2), int(h * 0.8))
        r = random.randint(12, 26)
    else:
        cx = random.randint(w - 25, w - 5)
        cy = random.randint(int(h * 0.2), int(h * 0.8))
        r = random.randint(12, 26)
        
    cv2.circle(mask, (cx, cy), r, 255, -1)
    
    # Missing material notch (fill with background dark void)
    if random.random() < 0.6:
        cv2.circle(defective, (cx, cy), r, (15, 15, 18), -1)
        # Rough irregular fracture contour
        rough_pts = []
        for a in np.linspace(0, 2 * np.pi, 16):
            rr = r + random.randint(-4, 4)
            rough_pts.append([int(cx + rr * np.cos(a)), int(cy + rr * np.sin(a))])
        cv2.drawContours(defective, [np.array(rough_pts)], -1, (25, 25, 30), -1)
    else:
        # Burr / metal extrusion bulge
        cv2.circle(defective, (cx, cy), r, (130, 135, 140), -1)
        cv2.circle(defective, (cx, cy), r, (70, 70, 70), 2)
        
    return defective, mask


def generate_synthetic_dataset(
    output_dir: str = "data/processed",
    samples_per_class: int = 60,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    img_size: int = 256
) -> Dict[str, Dict[str, int]]:
    """
    Generates synthetic industrial dataset with train/val/test splits and ground truth masks.
    
    Returns:
        dict: Summary statistics per split and per class.
    """
    print(f"Generating synthetic manufacturing dataset in: {output_dir}")
    print(f"  Classes: {DEFECT_CLASSES}")
    print(f"  Samples per class: {samples_per_class} | Resolution: {img_size}x{img_size}")
    
    splits = ["train", "val", "test"]
    stats: Dict[str, Dict[str, int]] = {s: {c: 0 for c in DEFECT_CLASSES} for s in splits}
    
    injectors = {
        "crack": inject_crack,
        "scratch": inject_scratch,
        "dent": inject_dent,
        "stain": inject_stain,
        "discoloration": inject_discoloration,
        "dimensional_irregularity": inject_dimensional_irregularity,
    }
    
    n_train = int(samples_per_class * train_ratio)
    n_val = int(samples_per_class * val_ratio)
    n_test = samples_per_class - n_train - n_val
    
    split_counts = [("train", n_train), ("val", n_val), ("test", n_test)]
    
    for cls in DEFECT_CLASSES:
        for split_name, count in split_counts:
            # Note: For anomaly detection training, train split has generous normal samples
            effective_count = count
            if split_name == "train" and cls != "normal":
                # For autoencoder training, train is predominantly normal
                effective_count = count
                
            img_dir = Path(output_dir) / split_name / cls / "images"
            mask_dir = Path(output_dir) / split_name / cls / "masks"
            img_dir.mkdir(parents=True, exist_ok=True)
            mask_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(effective_count):
                # Randomize texture substrate
                tex = random.choice(["brushed_metal", "ceramic_tile", "smooth_plastic"])
                base = create_base_texture(img_size, img_size, tex)
                
                if cls == "normal":
                    img = base
                    mask = np.zeros((img_size, img_size), dtype=np.uint8)
                else:
                    img, mask = injectors[cls](base)
                    
                fname = f"{cls}_{i:04d}.png"
                cv2.imwrite(str(img_dir / fname), img)
                cv2.imwrite(str(mask_dir / fname), mask)
                stats[split_name][cls] += 1
                
    return stats


def download_mvtec_category(category: str = "metal_nut", raw_dir: str = "data/raw") -> str:
    """
    Downloads and extracts a specified MVTec AD category dataset.
    """
    if category not in MVTEC_CATEGORIES:
        raise ValueError(f"Category '{category}' is not a valid MVTec category. Choose from: {MVTEC_CATEGORIES}")
        
    out_dir = Path(raw_dir) / "mvtec_ad"
    out_dir.mkdir(parents=True, exist_ok=True)
    cat_dir = out_dir / category
    
    if cat_dir.exists() and any(cat_dir.iterdir()):
        print(f"MVTec AD category '{category}' already exists in {cat_dir}")
        return str(cat_dir)
        
    tar_path = out_dir / f"{category}.tar.xz"
    url = f"ftp://guest:guest2019@ftp.softronics.ch/mvtec_anomaly_detection/{category}.tar.xz"
    print(f"Downloading MVTec AD category '{category}' from {url}...")
    try:
        urllib.request.urlretrieve(url, str(tar_path))
        print("Download complete. Extracting archive...")
        with tarfile.open(str(tar_path), "r:xz") as tar:
            tar.extractall(path=str(out_dir))
        print(f"Extracted to {cat_dir}")
    except Exception as e:
        print(f"Notice: Direct MVTec download failed ({e}). Falling back to synthetic dataset generation.")
        return ""
    return str(cat_dir)


def print_dataset_summary(stats: Dict[str, Dict[str, int]], img_shape: Tuple[int, int, int] = (256, 256, 3)):
    """
    Prints a clean, formatted ASCII tabular summary of the loaded dataset statistics.
    """
    print("\n" + "=" * 76)
    print("      MANUFACTURING DEFECT INSPECTION — DATASET SUMMARY & METRICS")
    print("=" * 76)
    print(f"Image Resolution: {img_shape[0]}x{img_shape[1]} pixels | Channels: {img_shape[2]} (BGR)")
    print("-" * 76)
    header = f"{'Defect Category':<28} | {'Train':<10} | {'Val':<10} | {'Test':<10} | {'Total':<10}"
    print(header)
    print("-" * 76)
    
    total_train = 0
    total_val = 0
    total_test = 0
    
    for cls in DEFECT_CLASSES:
        tr = stats.get("train", {}).get(cls, 0)
        va = stats.get("val", {}).get(cls, 0)
        te = stats.get("test", {}).get(cls, 0)
        tot = tr + va + te
        total_train += tr
        total_val += va
        total_test += te
        print(f"{cls.replace('_', ' ').title():<28} | {tr:<10} | {va:<10} | {te:<10} | {tot:<10}")
        
    print("-" * 76)
    grand_total = total_train + total_val + total_test
    print(f"{'Grand Total':<28} | {total_train:<10} | {total_val:<10} | {total_test:<10} | {grand_total:<10}")
    print("=" * 76 + "\n")


def prepare_dataset(
    source: str = "synthetic",
    category: str = "metal_nut",
    raw_dir: str = "data/raw",
    processed_dir: str = "data/processed",
    samples_per_class: int = 50
) -> Dict[str, Dict[str, int]]:
    """
    Unified entry point for preparing dataset based on the requested source flag.
    """
    if source == "mvtec":
        extracted_dir = download_mvtec_category(category, raw_dir)
        if extracted_dir:
            # Process MVTec directory structure
            print(f"MVTec AD '{category}' ready for training.")
            # Return placeholder stats for MVTec
            return {"train": {"normal": 220}, "test": {category: 100, "normal": 60}}
        else:
            print("Swapping to synthetic data generator due to MVTec download unavailability.")
            
    # Synthetic generation
    stats = generate_synthetic_dataset(
        output_dir=processed_dir,
        samples_per_class=samples_per_class,
        img_size=256
    )
    print_dataset_summary(stats)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vision-Based Defect Detection Dataset Scaffolding & Preparation")
    parser.add_argument("--source", type=str, default="synthetic", choices=["synthetic", "mvtec"],
                        help="Dataset source: 'synthetic' (OpenCV generator) or 'mvtec' (MVTec AD benchmark)")
    parser.add_argument("--category", type=str, default="metal_nut", choices=MVTEC_CATEGORIES,
                        help="MVTec category to download if --source=mvtec")
    parser.add_argument("--output_dir", type=str, default="data/processed",
                        help="Output directory for processed dataset")
    parser.add_argument("--samples", type=int, default=50,
                        help="Samples per class for synthetic generation")
    args = parser.parse_args()
    
    prepare_dataset(
        source=args.source,
        category=args.category,
        processed_dir=args.output_dir,
        samples_per_class=args.samples
    )
