#!/usr/bin/env python3
"""
prepare_dataset.py
------------------
Convenience root script to prepare MVTec AD or generate OpenCV synthetic manufacturing defects.
Run with:
    python3 prepare_dataset.py --source synthetic --samples 50
    python3 prepare_dataset.py --source mvtec --category metal_nut
"""
import sys
import argparse
from src.dataset import prepare_dataset, DEFECT_CLASSES, MVTEC_CATEGORIES

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Industrial Defect Detection Dataset Scaffolding")
    parser.add_argument("--source", type=str, default="synthetic", choices=["synthetic", "mvtec"],
                        help="Dataset source: 'synthetic' or 'mvtec'")
    parser.add_argument("--category", type=str, default="metal_nut", choices=MVTEC_CATEGORIES,
                        help="MVTec category (used when --source=mvtec)")
    parser.add_argument("--output_dir", type=str, default="data/processed",
                        help="Directory to save train/val/test splits")
    parser.add_argument("--samples", type=int, default=50,
                        help="Number of synthetic samples per class")
    args = parser.parse_args()

    print(f"[*] Initializing Dataset Scaffolding [Source: {args.source.upper()}]...")
    stats = prepare_dataset(
        source=args.source,
        category=args.category,
        processed_dir=args.output_dir,
        samples_per_class=args.samples
    )
    print("[+] Dataset preparation completed successfully.")
