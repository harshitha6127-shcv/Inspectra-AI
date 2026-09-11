#!/usr/bin/env python3
"""
main.py - Vision-Based Defect Detection CLI Master Entry Point
=============================================================
Supports:
1. Direct inspection of image or folder (Prompt 7):
   python main.py --input path/to/image_or_folder

2. Quantitative evaluation & benchmarking (Prompt 6):
   python main.py --evaluate --samples 15

3. End-to-end demo batch simulation:
   python main.py --demo

4. Dataset preparation (Prompt 0):
   python main.py prepare --source synthetic --samples 50
"""

import os
import sys
import argparse
import time
from typing import List, Dict, Any
import cv2
import numpy as np

# Ensure src/ is on Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from dataset import prepare_dataset, DEFECT_CLASSES, create_base_texture, inject_crack, inject_scratch, inject_dent, inject_stain, inject_discoloration, inject_dimensional_irregularity
from preprocessing import preprocess_image, visualize_preprocessing_comparison
from pipeline import run_inspection, batch_inspection, DefectInspectionPipeline
from evaluate import run_evaluation


def print_run_summary(results: List[Dict[str, Any]], csv_path: str = ""):
    """
    Prints a formatted industrial run summary (Requirement 5 of Prompt 7):
    - total images processed
    - defects found
    - defect type breakdown
    - average inference time per image
    """
    total = len(results)
    if total == 0:
        print("[!] No results to summarize.")
        return

    defects_found = sum(1 for r in results if r.get("is_defective", False))
    pass_count = total - defects_found

    # Breakdown by defect type
    breakdown: Dict[str, int] = {}
    severity_breakdown: Dict[str, int] = {"Minor": 0, "Major": 0, "Critical": 0, "None": 0}
    total_time = 0.0

    for r in results:
        dtype = r.get("defect_type", "normal")
        breakdown[dtype] = breakdown.get(dtype, 0) + 1
        sev = r.get("severity_category", "None")
        severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1
        total_time += r.get("inference_time_ms", 0.0)

    avg_time = total_time / max(1, total)

    print("\n" + "=" * 70)
    print("           INSPECTION BATCH EXECUTION RUN SUMMARY")
    print("=" * 70)
    print(f"  • Total Images Processed:       {total}")
    print(f"  • Conforming Parts (PASS):      {pass_count} ({pass_count / total * 100:.1f}%)")
    print(f"  • Non-Conforming (DEFECTIVE):   {defects_found} ({defects_found / total * 100:.1f}%)")
    print(f"  • Average Inference Latency:    {avg_time:.2f} ms/image ({1000.0 / max(1.0, avg_time):.1f} FPS)")
    if csv_path:
        print(f"  • Batch Summary CSV Saved:      {csv_path}")
    print("-" * 70)
    print("  DEFECT TYPE BREAKDOWN:")
    for dtype, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {dtype.replace('_', ' ').title():<26} : {count:3d} ({count / total * 100:5.1f}%)")
    print("-" * 70)
    print("  SEVERITY CATEGORY BREAKDOWN:")
    for sev, count in severity_breakdown.items():
        if count > 0:
            print(f"    - {sev:<26} : {count:3d} ({count / total * 100:5.1f}%)")
    print("=" * 70 + "\n")


def run_demo():
    print("=" * 70)
    print("  VISION-BASED DEFECT DETECTION — END-TO-END DEMO INGESTION")
    print("=" * 70)

    demo_dir = "outputs/demo_batch"
    os.makedirs(demo_dir, exist_ok=True)

    test_cases = [
        ("sample_normal_01.png", create_base_texture(256, 256, "brushed_metal")),
        ("sample_crack_02.png", inject_crack(create_base_texture(256, 256, "brushed_metal"))[0]),
        ("sample_scratch_03.png", inject_scratch(create_base_texture(256, 256, "brushed_metal"))[0]),
        ("sample_dent_04.png", inject_dent(create_base_texture(256, 256, "brushed_metal"))[0]),
        ("sample_stain_05.png", inject_stain(create_base_texture(256, 256, "ceramic_tile"))[0]),
        ("sample_discolor_06.png", inject_discoloration(create_base_texture(256, 256, "brushed_metal"))[0]),
        ("sample_dimensional_07.png", inject_dimensional_irregularity(create_base_texture(256, 256, "brushed_metal"))[0]),
    ]

    saved_paths = []
    for fname, img in test_cases:
        p = os.path.join(demo_dir, fname)
        cv2.imwrite(p, img)
        saved_paths.append(p)

    results, csv_path = batch_inspection(saved_paths, output_dir="outputs", csv_filename="demo_batch_summary.csv")
    print_run_summary(results, csv_path=csv_path)


def handle_input(input_target: str, output_dir: str = "outputs"):
    """
    Handles file or folder path passed via --input argument (Prompt 7).
    """
    if not os.path.exists(input_target):
        print(f"[-] Error: Input path '{input_target}' does not exist.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    if os.path.isfile(input_target):
        print(f"[*] Inspecting individual image: {input_target}")
        res = run_inspection(input_target, output_dir=output_dir, save_annotation=True)
        print_run_summary([res])
        print(f"[+] Output visual overlay: {res.get('annotated_image_path')}")
    else:
        print(f"[*] Inspecting batch directory: {input_target}")
        results, csv_path = batch_inspection(input_target, output_dir=output_dir, csv_filename="batch_inspection_summary.csv")
        print_run_summary(results, csv_path=csv_path)


def main():
    parser = argparse.ArgumentParser(
        description="Vision-Based Defect Detection System for Manufacturing Quality Inspection"
    )

    # Prompt 7 primary argument: --input
    parser.add_argument("--input", type=str, default=None, help="Path to input image file or folder of images")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Directory where overlays and CSV are stored")
    
    # Flags for evaluation & demo
    parser.add_argument("--evaluate", action="store_true", help="Run quantitative evaluation benchmark (Prompt 6)")
    parser.add_argument("--samples", type=int, default=15, help="Samples per class for evaluation")
    parser.add_argument("--demo", action="store_true", help="Run end-to-end pipeline demonstration")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Additional commands")

    # prepare subcommand
    prep_p = subparsers.add_parser("prepare", help="Download MVTec AD or generate synthetic dataset")
    prep_p.add_argument("--source", type=str, default="synthetic", choices=["synthetic", "mvtec"])
    prep_p.add_argument("--category", type=str, default="metal_nut")
    prep_p.add_argument("--samples", type=int, default=50)

    # preprocess subcommand
    subparsers.add_parser("preprocess", help="Verify CLAHE, Bilateral, and Letterboxing")

    # inspect subcommand
    insp_p = subparsers.add_parser("inspect", help="Inspect an individual image file")
    insp_p.add_argument("--image", type=str, required=True, help="Path to input image")

    args = parser.parse_args()

    # Route based on arguments
    if args.input:
        handle_input(args.input, output_dir=args.output_dir)
    elif args.evaluate:
        run_evaluation(samples_per_class=args.samples, output_dir=args.output_dir)
    elif args.demo:
        run_demo()
    elif args.command == "prepare":
        prepare_dataset(source=args.source, category=args.category, samples_per_class=args.samples)
    elif args.command == "preprocess":
        base = create_base_texture(256, 256, "brushed_metal")
        crack, _ = inject_crack(base)
        scratch, _ = inject_scratch(base)
        visualize_preprocessing_comparison([("Crack Defect", crack), ("Surface Scratch", scratch)], save_path="outputs/preprocessing_comparison.png")
    elif args.command == "inspect":
        handle_input(args.image, output_dir=args.output_dir)
    else:
        # Default behavior: run demo if no arguments passed
        run_demo()


if __name__ == "__main__":
    main()
