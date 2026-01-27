#!/usr/bin/env python3
"""
Automated Dustin Steele Voice Training

Fully automates RVC voice cloning:
1. Prepares dataset from extracted audio
2. Starts RVC server (native MPS mode - low RAM)
3. Automates training via Playwright
4. Monitors progress and saves model

Usage:
    python3 train_dustin_voice.py           # Full training
    python3 train_dustin_voice.py --check   # Check status only
    python3 train_dustin_voice.py --prepare # Prepare dataset only
"""

import os
import sys
import subprocess
import shutil
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Paths
RVC_DIR = Path.home() / "Projects/RVC/rvc-webui"
DATASETS_DIR = RVC_DIR / "datasets"
WEIGHTS_DIR = RVC_DIR / "assets/weights"
LOGS_DIR = RVC_DIR / "logs"

# Training data sources
TRAINING_SOURCES = [
    Path("/Volumes/David External/SAM_Voice_Training/dustin_moaning"),
    Path("/Volumes/David External/SAM_Voice_Training/extracted_dustin_full"),
    Path("/Volumes/David External/SAM_Voice_Training/extracted_dustin"),
]

MODEL_NAME = "dustin_steele"
RVC_PORT = 7865


def check_status() -> Dict[str, Any]:
    """Check current training status."""
    status = {
        "dataset_ready": False,
        "features_extracted": False,
        "model_trained": False,
        "rvc_running": False,
    }

    # Check dataset
    dataset_dir = DATASETS_DIR / MODEL_NAME
    if dataset_dir.exists():
        audio_files = list(dataset_dir.glob("*.wav")) + list(dataset_dir.glob("*.mp3"))
        status["dataset_ready"] = len(audio_files) > 0
        status["audio_files"] = len(audio_files)

    # Check features
    logs_dir = LOGS_DIR / MODEL_NAME
    if logs_dir.exists():
        f0_files = list(logs_dir.glob("**/f0*.npy"))
        feature_files = list(logs_dir.glob("**/hubert*.npy"))
        status["features_extracted"] = len(f0_files) > 0
        status["f0_files"] = len(f0_files)
        status["feature_files"] = len(feature_files)

    # Check model
    model_files = list(WEIGHTS_DIR.glob(f"{MODEL_NAME}*.pth"))
    status["model_trained"] = len(model_files) > 0
    status["model_files"] = [str(f) for f in model_files]

    # Check if RVC is running
    try:
        import requests
        resp = requests.get(f"http://localhost:{RVC_PORT}", timeout=2)
        status["rvc_running"] = resp.status_code == 200
    except:
        status["rvc_running"] = False

    return status


def prepare_dataset() -> Dict[str, Any]:
    """Prepare training dataset from extracted audio."""
    dataset_dir = DATASETS_DIR / MODEL_NAME
    dataset_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    total_duration = 0

    for source_dir in TRAINING_SOURCES:
        if not source_dir.exists():
            continue

        for audio_file in source_dir.glob("*.wav"):
            dest = dataset_dir / audio_file.name
            if not dest.exists():
                shutil.copy2(audio_file, dest)
                copied += 1

            # Estimate duration
            try:
                import wave
                with wave.open(str(audio_file), 'rb') as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    total_duration += frames / rate
            except:
                pass

    audio_count = len(list(dataset_dir.glob("*.wav")))

    return {
        "success": True,
        "dataset_dir": str(dataset_dir),
        "files_copied": copied,
        "total_files": audio_count,
        "total_duration_minutes": total_duration / 60,
    }


def start_rvc_server() -> subprocess.Popen:
    """Start RVC WebUI server in native MPS mode."""
    script = Path.home() / "ReverseLab/SAM/scripts/rvc_native.sh"

    if not script.exists():
        # Create the script if it doesn't exist
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text("""#!/bin/bash
# RVC Native MPS Training (no Docker, ~336MB RAM)
cd ~/Projects/RVC/rvc-webui
source .venv/bin/activate
python infer-web.py
""")
        script.chmod(0o755)

    # Start in background
    process = subprocess.Popen(
        ["bash", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(RVC_DIR),
    )

    return process


def wait_for_rvc_ready(timeout: int = 120) -> bool:
    """Wait for RVC server to be ready."""
    import requests

    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"http://localhost:{RVC_PORT}", timeout=2)
            if resp.status_code == 200:
                return True
        except:
            pass
        time.sleep(2)

    return False


async def automate_training():
    """Automate RVC training via Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Installing playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        page = await browser.new_page()

        print("Opening RVC WebUI...")
        await page.goto(f"http://localhost:{RVC_PORT}")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Navigate to Train tab
        print("Clicking Train tab...")
        try:
            await page.click("button:has-text('Train')")
        except:
            # Try alternative selector
            tabs = await page.query_selector_all("button")
            for tab in tabs:
                text = await tab.inner_text()
                if "train" in text.lower():
                    await tab.click()
                    break

        await asyncio.sleep(2)

        # Fill experiment name
        print(f"Setting experiment name: {MODEL_NAME}")
        textareas = await page.query_selector_all("textarea:visible")

        for textarea in textareas[:3]:
            value = await textarea.input_value() or ""
            if "mi-test" in value or len(value) < 30:
                await textarea.fill(MODEL_NAME)
                break

        await asyncio.sleep(1)

        # Find and click "1. Process Data" if needed
        buttons = await page.query_selector_all("button:visible")

        process_btn = None
        feature_btn = None
        train_btn = None

        for btn in buttons:
            text = (await btn.inner_text()).lower()
            if "process data" in text or "1. process" in text:
                process_btn = btn
            elif "feature" in text:
                feature_btn = btn
            elif "train model" in text or "3. train" in text:
                train_btn = btn

        # Check if we need to process
        status = check_status()

        if not status["features_extracted"]:
            if process_btn:
                print("Processing data...")
                await process_btn.click()
                await asyncio.sleep(30)  # Wait for processing

            if feature_btn:
                print("Extracting features...")
                await feature_btn.click()
                await asyncio.sleep(60)  # Wait for extraction
        else:
            print(f"Features already extracted: {status.get('f0_files', 0)} F0 files")

        # Start training
        if train_btn:
            print("Starting training...")
            await train_btn.click()
            await asyncio.sleep(5)

            print("\n=== Training Started ===")
            print(f"Model: {MODEL_NAME}")
            print(f"WebUI: http://localhost:{RVC_PORT}")
            print("Training typically takes 1-6 hours depending on data size")
            print("Monitor progress in the WebUI console")
            print("\nPress Ctrl+C when training completes")

            # Keep browser open for monitoring
            try:
                while True:
                    await asyncio.sleep(60)
                    # Check if model file appeared
                    model_files = list(WEIGHTS_DIR.glob(f"{MODEL_NAME}*.pth"))
                    if model_files:
                        print(f"\n=== Model Saved! ===")
                        print(f"Model file: {model_files[0]}")
                        break
            except KeyboardInterrupt:
                print("\nTraining monitoring stopped")

        await browser.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Automate Dustin Steele voice training")
    parser.add_argument("--check", action="store_true", help="Check status only")
    parser.add_argument("--prepare", action="store_true", help="Prepare dataset only")
    parser.add_argument("--train", action="store_true", help="Start training (default)")
    args = parser.parse_args()

    if args.check:
        status = check_status()
        print(json.dumps(status, indent=2))
        return

    if args.prepare:
        result = prepare_dataset()
        print(json.dumps(result, indent=2))
        return

    # Full training flow
    print("=== Dustin Steele Voice Training ===\n")

    # 1. Check current status
    status = check_status()
    print(f"Status: {json.dumps(status, indent=2)}\n")

    if status["model_trained"]:
        print("Model already trained!")
        print(f"Model files: {status['model_files']}")
        return

    # 2. Prepare dataset
    if not status["dataset_ready"]:
        print("Preparing dataset...")
        result = prepare_dataset()
        print(f"Dataset: {result['total_files']} files, {result['total_duration_minutes']:.1f} minutes\n")

    # 3. Start RVC server if not running
    rvc_process = None
    if not status["rvc_running"]:
        print("Starting RVC server (native MPS mode)...")
        rvc_process = start_rvc_server()

        print("Waiting for server to be ready...")
        if not wait_for_rvc_ready():
            print("ERROR: RVC server failed to start")
            return
        print("RVC server ready!\n")

    # 4. Automate training
    try:
        asyncio.run(automate_training())
    except KeyboardInterrupt:
        print("\nTraining interrupted")
    finally:
        if rvc_process:
            rvc_process.terminate()

    # 5. Final status
    final_status = check_status()
    if final_status["model_trained"]:
        print("\n=== SUCCESS ===")
        print(f"Model saved: {final_status['model_files']}")
    else:
        print("\n=== Training may still be in progress ===")
        print("Check the RVC WebUI for status")


if __name__ == "__main__":
    main()
