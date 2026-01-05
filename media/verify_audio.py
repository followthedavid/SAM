#!/usr/bin/env python3
"""
Audio File Integrity Verifier
Checks all audio files for corruption using format-specific tools.

- FLAC: Uses flac -t (native test)
- ALAC/M4A/AAC: Uses ffmpeg decode test
- MP3: Uses mp3val or ffmpeg
- WAV: Uses ffmpeg
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

def verify_flac(filepath):
    """Verify FLAC file integrity"""
    try:
        result = subprocess.run(
            ['flac', '-t', '-s', str(filepath)],
            capture_output=True,
            timeout=60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except FileNotFoundError:
        # flac not installed, fall back to ffmpeg
        return verify_with_ffmpeg(filepath)
    except Exception:
        return False

def verify_with_ffmpeg(filepath):
    """Verify audio file by decoding with ffmpeg"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(filepath), '-f', 'null', '-'],
            capture_output=True,
            timeout=120
        )
        # Check for errors in stderr
        errors = result.stderr.decode('utf-8', errors='ignore')
        # Some warnings are OK, look for actual errors
        critical_errors = ['Invalid', 'corrupt', 'error', 'failed', 'Could not']
        has_critical = any(err.lower() in errors.lower() for err in critical_errors)
        return result.returncode == 0 and not has_critical
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False

def verify_file(filepath):
    """Verify a single audio file"""
    ext = filepath.suffix.lower()

    if ext == '.flac':
        return verify_flac(filepath)
    elif ext in ['.m4a', '.mp4', '.aac', '.alac', '.mp3', '.wav', '.wave', '.wma', '.ogg']:
        return verify_with_ffmpeg(filepath)
    else:
        # Unknown format, skip
        return True

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
    print("=" * 60)
    print("SAM AUDIO INTEGRITY VERIFIER")
    print("=" * 60)
    print(f"Scanning: {MUSIC_DIR}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Find all audio files
    print("Finding audio files...")
    files = find_audio_files(MUSIC_DIR)
    total = len(files)
    print(f"Found {total:,} audio files to verify")
    print()

    # Track results
    verified = 0
    corrupted = []
    errors = []

    # Process with thread pool
    print("Verifying files (this may take a while)...")
    print()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(verify_file, f): f for f in files}

        for i, future in enumerate(as_completed(futures), 1):
            filepath = futures[future]
            try:
                is_valid = future.result()
                if is_valid:
                    verified += 1
                else:
                    corrupted.append(str(filepath))
                    print(f"  ❌ CORRUPTED: {filepath.name}")
            except Exception as e:
                errors.append({'file': str(filepath), 'error': str(e)})
                print(f"  ⚠️  ERROR: {filepath.name} - {e}")

            # Progress update every 100 files
            if i % 100 == 0 or i == total:
                pct = (i / total) * 100
                print(f"  Progress: {i:,}/{total:,} ({pct:.1f}%) - {len(corrupted)} corrupted found")

    # Save results
    results = {
        'scan_date': datetime.now().isoformat(),
        'directory': str(MUSIC_DIR),
        'total_files': total,
        'verified_ok': verified,
        'corrupted_count': len(corrupted),
        'error_count': len(errors),
        'corrupted_files': corrupted,
        'errors': errors
    }

    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

    # Save corrupted file list
    if corrupted:
        with open(CORRUPTED_LOG, 'w') as f:
            f.write(f"# Corrupted files found {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(corrupted)}\n\n")
            for filepath in corrupted:
                f.write(f"{filepath}\n")

    # Summary
    print()
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print(f"Total files:    {total:,}")
    print(f"Verified OK:    {verified:,}")
    print(f"Corrupted:      {len(corrupted):,}")
    print(f"Errors:         {len(errors):,}")
    print()
    print(f"Results saved:  {RESULTS_FILE}")
    if corrupted:
        print(f"Corrupted list: {CORRUPTED_LOG}")
        print()
        print("⚠️  CORRUPTED FILES FOUND - Review and replace these files")
    else:
        print()
        print("✅ All files verified successfully!")

    return len(corrupted) == 0

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
