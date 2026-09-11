"""
src/live_inspection.py - Local OpenCV Live Camera Feed Inspection Script
========================================================================
Prompt 10 Implementation:
1. Opens local optical camera sensor via cv2.VideoCapture.
2. Evaluates frames automatically every N seconds (default 2s) or on keypress ('c').
3. Runs frame through run_inspection() and overlays defect status, severity, confidence, and boxes.
4. Includes simulated test mode (--simulate) for headless or container environments.
"""

import os
import sys
import time
import argparse
from typing import Optional
import numpy as np
import cv2

# Ensure src/ is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pipeline import run_inspection, visualize_inspection_result
from dataset import create_base_texture, inject_crack, inject_scratch, inject_dent


def run_live_inspection(
    camera_index: int = 0,
    interval_sec: float = 2.0,
    simulate: bool = False,
    output_dir: str = "outputs"
):
    print("=" * 70)
    print("  VISION-BASED DEFECT DETECTION — LIVE WEBCAM INSPECTOR (PROMPT 10)")
    print("=" * 70)
    print(f"  • Interval Auto-Capture: Every {interval_sec}s")
    print("  • Controls:")
    print("      [c] : Force capture & immediate inspection")
    print("      [s] : Save current annotated frame to disk")
    print("      [q] / [ESC] : Quit live inspection")
    print("=" * 70)

    cap = None
    if not simulate:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"[!] Warning: Camera index {camera_index} could not be opened.")
            print("[*] Falling back to automated synthetic video simulation loop.")
            simulate = True

    os.makedirs(output_dir, exist_ok=True)
    last_inspection_time = 0.0
    last_result = None
    frame_count = 0
    sim_case_idx = 0

    sim_cases = [
        ("Normal Component", create_base_texture(320, 320, "brushed_metal")),
        ("Crack Defect", inject_crack(create_base_texture(320, 320, "brushed_metal"))[0]),
        ("Surface Scratch", inject_scratch(create_base_texture(320, 320, "brushed_metal"))[0]),
        ("Impact Dent", inject_dent(create_base_texture(320, 320, "brushed_metal"))[0]),
    ]

    try:
        while True:
            current_time = time.time()

            # 1. Grab frame from camera or simulator
            if not simulate and cap is not None:
                ret, frame = cap.read()
                if not ret:
                    print("[-] Failed to grab frame from camera. Exiting.")
                    break
            else:
                # Simulation mode: rotate through sample defects every 5 seconds
                sim_name, frame = sim_cases[(int(current_time // 5)) % len(sim_cases)]
                frame = frame.copy()
                time.sleep(0.03)  # ~30 FPS throttle

            display_frame = frame.copy()
            h, w = display_frame.shape[:2]

            # 2. Check if inspection trigger condition met
            trigger_inspection = (current_time - last_inspection_time) >= interval_sec

            if trigger_inspection or last_result is None:
                last_inspection_time = current_time
                last_result = run_inspection(frame, output_dir=output_dir, save_annotation=False)
                frame_count += 1

            # 3. Overlay Latest Inspection Status on Live Feed
            if last_result is not None:
                is_def = last_result.get("is_defective", False)
                sev = last_result.get("severity_category", "None")
                status_color = (40, 40, 235) if sev == "Critical" else (30, 200, 245) if sev == "Major" else (50, 200, 50)

                # Top HUD bar
                cv2.rectangle(display_frame, (0, 0), (w, 34), (20, 20, 20), -1)
                status_text = (
                    f"DEFECT [{sev.upper()}]: {last_result.get('defect_type', 'UNKNOWN').upper()} ({last_result.get('confidence', 0.0):.1%})"
                    if is_def else f"PASS: CONFORMING ({last_result.get('confidence', 0.0):.1%})"
                )
                cv2.putText(display_frame, status_text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1, cv2.LINE_AA)

                # Draw bounding boxes if any
                boxes = last_result.get("bounding_boxes", [])
                for idx, b in enumerate(boxes):
                    if len(b) == 4:
                        bx, by, bw, bh = b
                        cv2.rectangle(display_frame, (bx, by), (bx + bw, by + bh), status_color, 2)
                        cv2.putText(display_frame, f"#{idx+1} {sev}", (bx, max(14, by - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, status_color, 1, cv2.LINE_AA)

                # Bottom action HUD
                action_str = f"Action: {last_result.get('recommended_action', 'None')} | Latency: {last_result.get('inference_time_ms', 0)}ms"
                cv2.rectangle(display_frame, (0, h - 22), (w, h), (15, 15, 15), -1)
                cv2.putText(display_frame, action_str, (10, h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)

            # In headless environments (where cv2.imshow is unavailable), log and break after demo run
            try:
                cv2.imshow("Vision-Based Defect Detection — Live Camera Feed", display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key in [ord("q"), 27]:
                    break
                elif key == ord("c"):
                    # Force immediate re-inspection
                    last_result = run_inspection(frame, output_dir=output_dir, save_annotation=False)
                    last_inspection_time = time.time()
                elif key == ord("s"):
                    save_name = os.path.join(output_dir, f"live_snapshot_{int(time.time())}.png")
                    cv2.imwrite(save_name, display_frame)
                    print(f"[+] Saved snapshot to {save_name}")
            except cv2.error:
                # Headless mode detected (no GUI display server)
                print(f"[*] Headless environment detected. Inspected frame #{frame_count}: {last_result['decision']} - {last_result['defect_type']} (Severity: {last_result['severity_category']})")
                if frame_count >= 5:
                    print("[+] Live inspection test completed successfully in headless container.")
                    break

    finally:
        if cap is not None:
            cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        print("[*] Live inspection session ended.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Camera Feed Defect Inspection")
    parser.add_argument("--camera-index", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--interval", type=float, default=2.0, help="Inspection interval in seconds (default: 2.0s)")
    parser.add_argument("--simulate", action="store_true", help="Simulate video feed using synthetic defects")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Directory to save snapshots")
    args = parser.parse_args()

    run_live_inspection(
        camera_index=args.camera_index,
        interval_sec=args.interval,
        simulate=args.simulate,
        output_dir=args.output_dir
    )
