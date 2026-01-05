#!/usr/bin/env python3
"""
SAM Audio Quality Analyzer
Comprehensive verification that checks:
1. File integrity (can it decode?)
2. Spectral analysis (is it truly lossless or upconverted from lossy?)
3. Bit depth verification (is 24-bit actually 24-bit?)
4. Sample rate validation

Replaces Fakin' the Funk functionality with open source tools.
"""

import subprocess
import os
import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict

MUSIC_DIR = Path("/Volumes/Music/_Music Lossless")
RESULTS_FILE = Path.home() / ".sam_quality_analysis.json"
REPORT_FILE = Path.home() / ".sam_quality_report.txt"

@dataclass
class AudioAnalysis:
    filepath: str
    valid: bool
    format: str
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float

    # Quality indicators
    claimed_lossless: bool
    actual_quality: str  # 'lossless', 'lossy-source', 'uncertain'
    frequency_cutoff: Optional[int]  # Hz where audio cuts off
    confidence: float  # 0-100%

    issues: List[str]
    warnings: List[str]


def get_audio_info(filepath: Path) -> Dict:
    """Get basic audio file information using ffprobe"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(filepath)
        ], capture_output=True, timeout=30)

        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return {}


def analyze_spectrum(filepath: Path) -> Dict:
    """
    Analyze frequency spectrum to detect lossy transcodes.

    True lossless: Energy up to ~22kHz (for 44.1kHz) or higher
    MP3 128kbps: Cutoff around 16kHz
    MP3 192kbps: Cutoff around 19kHz
    MP3 320kbps: Cutoff around 20kHz (harder to detect)
    AAC: Variable, usually higher than MP3
    """
    try:
        # Use sox to get frequency statistics
        # Generate a spectrogram data file
        result = subprocess.run([
            'sox', str(filepath), '-n', 'stat', '-freq'
        ], capture_output=True, timeout=120, text=True)

        # Parse the frequency data
        # sox stat -freq outputs frequency bins and their energy
        stderr = result.stderr

        # Alternative: use ffmpeg to check for frequency content
        # We'll sample the audio and check for energy in high frequencies
        result2 = subprocess.run([
            'sox', str(filepath), '-n', 'stats'
        ], capture_output=True, timeout=60, text=True)

        stats = {}
        for line in result2.stderr.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                stats[key.strip()] = val.strip()

        return stats

    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except Exception as e:
        return {'error': str(e)}


def detect_frequency_cutoff(filepath: Path, sample_rate: int) -> tuple:
    """
    Detect if there's a hard frequency cutoff indicating lossy source.
    Returns (cutoff_hz, confidence)
    """
    try:
        # Use ffmpeg to create a spectrogram and analyze it
        # We'll check for energy in frequency bands

        nyquist = sample_rate / 2

        # Quick method: check if there's audio content above certain thresholds
        # by using sox to analyze frequency bands

        # Test for content at different frequency thresholds
        thresholds = [
            (20000, 'likely-lossless'),
            (19000, 'possibly-320kbps'),
            (16000, 'possibly-192kbps'),
            (15000, 'possibly-128kbps'),
        ]

        # Use sox to get RMS energy in high frequency band
        result = subprocess.run([
            'sox', str(filepath), '-n',
            'highpass', '18000',  # Filter to only high frequencies
            'stats'
        ], capture_output=True, timeout=60, text=True)

        # Check if there's significant energy above 18kHz
        high_freq_energy = 0
        for line in result.stderr.split('\n'):
            if 'RMS lev dB' in line:
                try:
                    db = float(line.split()[-1])
                    high_freq_energy = db
                except:
                    pass

        # If high frequency energy is very low (< -60dB), likely lossy source
        if high_freq_energy < -70:
            return (16000, 80)  # Likely MP3, 80% confidence
        elif high_freq_energy < -55:
            return (19000, 60)  # Possibly high-bitrate lossy, 60% confidence
        else:
            return (None, 90)  # Likely true lossless, 90% confidence

    except Exception as e:
        return (None, 0)  # Can't determine


def verify_bit_depth(filepath: Path, claimed_bits: int) -> tuple:
    """
    Verify actual bit depth matches claimed.
    Some files claim 24-bit but are actually 16-bit padded.
    Returns (actual_bits, is_padded)
    """
    try:
        # Use sox to analyze bit distribution
        result = subprocess.run([
            'sox', str(filepath), '-n', 'stats'
        ], capture_output=True, timeout=60, text=True)

        # Look for "Bit-depth" in output
        for line in result.stderr.split('\n'):
            if 'Bit-depth' in line:
                match = re.search(r'(\d+)/(\d+)', line)
                if match:
                    actual = int(match.group(1))
                    container = int(match.group(2))
                    return (actual, actual < container)

        return (claimed_bits, False)

    except Exception:
        return (claimed_bits, False)


def analyze_file(filepath: Path) -> AudioAnalysis:
    """Comprehensive analysis of a single audio file"""

    issues = []
    warnings = []

    # Get basic info
    info = get_audio_info(filepath)

    if not info:
        return AudioAnalysis(
            filepath=str(filepath),
            valid=False,
            format='unknown', sample_rate=0, bit_depth=0,
            channels=0, duration=0,
            claimed_lossless=False, actual_quality='error',
            frequency_cutoff=None, confidence=0,
            issues=['Could not read file'],
            warnings=[]
        )

    # Extract stream info
    audio_stream = None
    for stream in info.get('streams', []):
        if stream.get('codec_type') == 'audio':
            audio_stream = stream
            break

    if not audio_stream:
        return AudioAnalysis(
            filepath=str(filepath),
            valid=False,
            format='unknown', sample_rate=0, bit_depth=0,
            channels=0, duration=0,
            claimed_lossless=False, actual_quality='error',
            frequency_cutoff=None, confidence=0,
            issues=['No audio stream found'],
            warnings=[]
        )

    codec = audio_stream.get('codec_name', 'unknown')
    sample_rate = int(audio_stream.get('sample_rate', 0))
    bit_depth = int(audio_stream.get('bits_per_raw_sample', 0) or
                   audio_stream.get('bits_per_sample', 16))
    channels = int(audio_stream.get('channels', 0))
    duration = float(info.get('format', {}).get('duration', 0))

    # Determine if format claims to be lossless
    lossless_codecs = ['flac', 'alac', 'wav', 'aiff', 'pcm', 'ape', 'wavpack']
    claimed_lossless = any(lc in codec.lower() for lc in lossless_codecs)

    # Test file integrity
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(filepath), '-f', 'null', '-'],
            capture_output=True, timeout=180
        )
        valid = result.returncode == 0
        if not valid:
            issues.append(f"Decode error: {result.stderr.decode()[:100]}")
    except subprocess.TimeoutExpired:
        valid = False
        issues.append("File decode timed out")
    except Exception as e:
        valid = False
        issues.append(f"Error: {str(e)}")

    # Spectral analysis for lossless files
    actual_quality = 'unknown'
    frequency_cutoff = None
    confidence = 0

    if valid and claimed_lossless:
        cutoff, conf = detect_frequency_cutoff(filepath, sample_rate)
        frequency_cutoff = cutoff
        confidence = conf

        if cutoff is None:
            actual_quality = 'lossless'
        elif cutoff <= 16000:
            actual_quality = 'lossy-source'
            issues.append(f"Likely transcoded from MP3 ~128-192kbps (cutoff at {cutoff}Hz)")
        elif cutoff <= 19000:
            actual_quality = 'uncertain'
            warnings.append(f"Possible high-bitrate lossy source (cutoff at {cutoff}Hz)")
        else:
            actual_quality = 'lossless'
    elif valid:
        actual_quality = 'lossy'  # Format is lossy (MP3, AAC, etc.)
        confidence = 100

    # Verify bit depth
    if valid and claimed_lossless and bit_depth >= 24:
        actual_bits, is_padded = verify_bit_depth(filepath, bit_depth)
        if is_padded:
            warnings.append(f"Claimed {bit_depth}-bit but actual content is {actual_bits}-bit")

    return AudioAnalysis(
        filepath=str(filepath),
        valid=valid,
        format=codec,
        sample_rate=sample_rate,
        bit_depth=bit_depth,
        channels=channels,
        duration=duration,
        claimed_lossless=claimed_lossless,
        actual_quality=actual_quality,
        frequency_cutoff=frequency_cutoff,
        confidence=confidence,
        issues=issues,
        warnings=warnings
    )


def find_audio_files(directory: Path) -> List[Path]:
    """Find all audio files in directory"""
    extensions = {'.flac', '.m4a', '.mp4', '.aac', '.mp3', '.wav', '.wave', '.wma', '.ogg', '.ape'}
    files = []

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_NEEDS_REPLACEMENT']

        for filename in filenames:
            if Path(filename).suffix.lower() in extensions:
                files.append(Path(root) / filename)

    return files


def main():
    print("=" * 70, flush=True)
    print("SAM AUDIO QUALITY ANALYZER", flush=True)
    print("Comprehensive integrity + quality verification", flush=True)
    print("=" * 70, flush=True)
    print(f"Directory: {MUSIC_DIR}", flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(flush=True)

    # Find files
    print("Finding audio files...", flush=True)
    files = find_audio_files(MUSIC_DIR)
    total = len(files)
    print(f"Found {total:,} files to analyze", flush=True)
    print(flush=True)

    # Track results
    results = {
        'corrupted': [],
        'fake_lossless': [],
        'padded_bitdepth': [],
        'valid_lossless': [],
        'valid_lossy': [],
        'warnings': []
    }

    print("Analyzing files (this takes longer than simple verification)...", flush=True)
    print(flush=True)

    # Process files (fewer workers due to heavier analysis)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(analyze_file, f): f for f in files}

        for i, future in enumerate(as_completed(futures), 1):
            filepath = futures[future]
            try:
                analysis = future.result()

                if not analysis.valid:
                    results['corrupted'].append(analysis)
                    print(f"  ❌ CORRUPTED: {Path(analysis.filepath).name}", flush=True)
                elif analysis.actual_quality == 'lossy-source':
                    results['fake_lossless'].append(analysis)
                    print(f"  🎭 FAKE LOSSLESS: {Path(analysis.filepath).name}", flush=True)
                    print(f"     {analysis.issues[0] if analysis.issues else ''}", flush=True)
                elif analysis.warnings:
                    results['warnings'].append(analysis)
                elif analysis.claimed_lossless:
                    results['valid_lossless'].append(analysis)
                else:
                    results['valid_lossy'].append(analysis)

            except Exception as e:
                print(f"  ⚠️ ERROR: {filepath.name} - {e}", flush=True)

            if i % 200 == 0 or i == total:
                pct = (i / total) * 100
                print(f"  Progress: {i:,}/{total:,} ({pct:.1f}%)", flush=True)
                print(f"    Corrupted: {len(results['corrupted'])}, Fake: {len(results['fake_lossless'])}, Warnings: {len(results['warnings'])}", flush=True)

    # Save results
    summary = {
        'scan_date': datetime.now().isoformat(),
        'directory': str(MUSIC_DIR),
        'total_files': total,
        'corrupted': len(results['corrupted']),
        'fake_lossless': len(results['fake_lossless']),
        'valid_lossless': len(results['valid_lossless']),
        'valid_lossy': len(results['valid_lossy']),
        'with_warnings': len(results['warnings']),
        'corrupted_files': [a.filepath for a in results['corrupted']],
        'fake_lossless_files': [{'file': a.filepath, 'issue': a.issues[0] if a.issues else ''}
                                for a in results['fake_lossless']],
        'warning_files': [{'file': a.filepath, 'warning': a.warnings[0] if a.warnings else ''}
                         for a in results['warnings'][:100]]
    }

    with open(RESULTS_FILE, 'w') as f:
        json.dump(summary, f, indent=2)

    # Generate report
    with open(REPORT_FILE, 'w') as f:
        f.write("SAM AUDIO QUALITY REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Total files analyzed: {total:,}\n\n")

        f.write("SUMMARY:\n")
        f.write(f"  ✅ Valid lossless:  {len(results['valid_lossless']):,}\n")
        f.write(f"  ✅ Valid lossy:     {len(results['valid_lossy']):,}\n")
        f.write(f"  ⚠️  With warnings:  {len(results['warnings']):,}\n")
        f.write(f"  🎭 Fake lossless:   {len(results['fake_lossless']):,}\n")
        f.write(f"  ❌ Corrupted:       {len(results['corrupted']):,}\n")
        f.write("\n")

        if results['corrupted']:
            f.write("=" * 70 + "\n")
            f.write("CORRUPTED FILES (need replacement):\n")
            f.write("=" * 70 + "\n")
            for a in results['corrupted']:
                f.write(f"\n{a.filepath}\n")
                for issue in a.issues:
                    f.write(f"  Error: {issue}\n")

        if results['fake_lossless']:
            f.write("\n" + "=" * 70 + "\n")
            f.write("FAKE LOSSLESS (transcoded from lossy source):\n")
            f.write("=" * 70 + "\n")
            for a in results['fake_lossless']:
                f.write(f"\n{a.filepath}\n")
                for issue in a.issues:
                    f.write(f"  Issue: {issue}\n")

    # Final summary
    print(flush=True)
    print("=" * 70, flush=True)
    print("ANALYSIS COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"Total files:      {total:,}", flush=True)
    print(f"Valid lossless:   {len(results['valid_lossless']):,}", flush=True)
    print(f"Valid lossy:      {len(results['valid_lossy']):,}", flush=True)
    print(f"With warnings:    {len(results['warnings']):,}", flush=True)
    print(f"🎭 FAKE LOSSLESS: {len(results['fake_lossless']):,}", flush=True)
    print(f"❌ CORRUPTED:     {len(results['corrupted']):,}", flush=True)
    print(flush=True)
    print(f"Full report: {REPORT_FILE}", flush=True)
    print(f"JSON data:   {RESULTS_FILE}", flush=True)

    if results['fake_lossless']:
        print(flush=True)
        print("⚠️  FAKE LOSSLESS FILES DETECTED", flush=True)
        print("These files claim to be lossless but were transcoded from lossy sources.", flush=True)
        print("Consider replacing with genuine lossless copies.", flush=True)

    if results['corrupted']:
        print(flush=True)
        print("❌ CORRUPTED FILES FOUND - These need replacement", flush=True)


if __name__ == '__main__':
    main()
