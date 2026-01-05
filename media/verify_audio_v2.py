#!/usr/bin/env python3
"""
Audio File Integrity Verifier v2
More accurate - only flags actual decode failures, not warnings.

Verification method:
- FLAC: Uses flac -t (native test) - exit code only
- Others: Uses ffmpeg decode - exit code only
- Warnings are logged separately but don't count as corruption
"""

import subprocess
import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

MUSIC_DIR = Path("/Volumes/Music/_Music Lossless")
RESULTS_FILE = Path.home() / ".sam_audio_verification.json"
CORRUPTED_LOG = Path.home() / ".sam_corrupted_files.txt"
WARNINGS_LOG = Path.home() / ".sam_audio_warnings.txt"

def verify_flac(filepath):
    """Verify FLAC file integrity using native flac test"""
    try:
        result = subprocess.run(
            ['flac', '-t', '-s', str(filepath)],
            capture_output=True,
            timeout=120
        )
        # Only exit code matters
        return {'valid': result.returncode == 0, 'warning': None}
    except subprocess.TimeoutExpired:
        return {'valid': False, 'warning': 'timeout'}
    except FileNotFoundError:
        return verify_with_ffmpeg(filepath)
    except Exception as e:
        return {'valid': False, 'warning': str(e)}

def verify_with_ffmpeg(filepath):
    """Verify audio file by decoding with ffmpeg - exit code only"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(filepath), '-f', 'null', '-'],
            capture_output=True,
            timeout=180
        )

        stderr = result.stderr.decode('utf-8', errors='ignore').strip()

        # Exit code is the definitive test
        # stderr warnings are noted but don't mean corruption
        if result.returncode == 0:
            return {'valid': True, 'warning': stderr if stderr else None}
        else:
            return {'valid': False, 'warning': stderr}

    except subprocess.TimeoutExpired:
        return {'valid': False, 'warning': 'timeout - file may be very large or corrupted'}
    except Exception as e:
        return {'valid': False, 'warning': str(e)}

def verify_file(filepath):
    """Verify a single audio file"""
    ext = filepath.suffix.lower()

    if ext == '.flac':
        return verify_flac(filepath)
    elif ext in ['.m4a', '.mp4', '.aac', '.alac', '.mp3', '.wav', '.wave', '.wma', '.ogg']:
        return verify_with_ffmpeg(filepath)
    else:
        return {'valid': True, 'warning': 'unknown format, skipped'}

def find_audio_files(directory):
    """Find all audio files in directory"""
    extensions = {'.flac', '.m4a', '.mp4', '.aac', '.mp3', '.wav', '.wave', '.wma', '.ogg'}
    files = []

    for root, dirs, filenames in os.walk(directory):
        # Skip hidden directories and special folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_NEEDS_REPLACEMENT']

        for filename in filenames:
            if Path(filename).suffix.lower() in extensions:
                files.append(Path(root) / filename)

    return files

def main():
    print("=" * 60, flush=True)
    print("SAM AUDIO INTEGRITY VERIFIER v2", flush=True)
    print("=" * 60, flush=True)
    print(f"Scanning: {MUSIC_DIR}", flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(flush=True)

    # Find all audio files
    print("Finding audio files...", flush=True)
    files = find_audio_files(MUSIC_DIR)
    total = len(files)
    print(f"Found {total:,} audio files to verify", flush=True)
    print(flush=True)

    # Track results
    verified = 0
    corrupted = []
    warnings = []

    # Process with thread pool
    print("Verifying files...", flush=True)
    print("(Only actual decode failures are flagged as corrupted)", flush=True)
    print(flush=True)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(verify_file, f): f for f in files}

        for i, future in enumerate(as_completed(futures), 1):
            filepath = futures[future]
            try:
                result = future.result()
                if result['valid']:
                    verified += 1
                    if result['warning']:
                        warnings.append({'file': str(filepath), 'warning': result['warning']})
                else:
                    corrupted.append({'file': str(filepath), 'error': result['warning']})
                    print(f"  ❌ CORRUPTED: {filepath.name}", flush=True)
                    print(f"     Reason: {result['warning']}", flush=True)
            except Exception as e:
                corrupted.append({'file': str(filepath), 'error': str(e)})
                print(f"  ❌ ERROR: {filepath.name} - {e}", flush=True)

            # Progress update every 500 files
            if i % 500 == 0 or i == total:
                pct = (i / total) * 100
                print(f"  Progress: {i:,}/{total:,} ({pct:.1f}%) - {len(corrupted)} corrupted, {len(warnings)} warnings", flush=True)

    # Save results
    results = {
        'scan_date': datetime.now().isoformat(),
        'directory': str(MUSIC_DIR),
        'total_files': total,
        'verified_ok': verified,
        'corrupted_count': len(corrupted),
        'warning_count': len(warnings),
        'corrupted_files': corrupted,
        'files_with_warnings': warnings[:100]  # First 100 warnings
    }

    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    # Save corrupted file list
    if corrupted:
        with open(CORRUPTED_LOG, 'w') as f:
            f.write(f"# Corrupted files found {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(corrupted)}\n\n")
            for item in corrupted:
                f.write(f"{item['file']}\n")
                f.write(f"  Error: {item['error']}\n\n")

    # Save warnings
    if warnings:
        with open(WARNINGS_LOG, 'w') as f:
            f.write(f"# Files with warnings (but playable) {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(warnings)}\n\n")
            for item in warnings[:100]:
                f.write(f"{item['file']}\n")
                f.write(f"  Warning: {item['warning']}\n\n")

    # Summary
    print(flush=True)
    print("=" * 60, flush=True)
    print("VERIFICATION COMPLETE", flush=True)
    print("=" * 60, flush=True)
    print(f"Total files:     {total:,}", flush=True)
    print(f"Verified OK:     {verified:,}", flush=True)
    print(f"With warnings:   {len(warnings):,} (playable but have minor issues)", flush=True)
    print(f"CORRUPTED:       {len(corrupted):,} (cannot decode)", flush=True)
    print(flush=True)
    print(f"Results: {RESULTS_FILE}", flush=True)

    if corrupted:
        print(f"Corrupted list: {CORRUPTED_LOG}", flush=True)
        print(flush=True)
        print("⚠️  CORRUPTED FILES FOUND - These need replacement", flush=True)
    else:
        print(flush=True)
        print("✅ All files verified successfully!", flush=True)

    if warnings:
        print(f"ℹ️  {len(warnings)} files have minor warnings but are playable", flush=True)

    return len(corrupted) == 0

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
