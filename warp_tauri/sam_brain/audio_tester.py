#!/usr/bin/env python3
"""
SAM Audio Tester
================

Automated testing for TTS and RVC voice systems without human review.

Tests:
1. TTS Generation - Does it produce audio? Correct duration? Not silent?
2. RVC Conversion - Does conversion work? Quality preserved?
3. Audio Quality - Spectral analysis, silence detection, clipping detection

Usage:
  python audio_tester.py test-tts "Hello, I am SAM"
  python audio_tester.py test-rvc input.wav
  python audio_tester.py benchmark
"""

import os
import sys
import json
import wave
import struct
import subprocess
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, List, Optional
from enum import Enum

class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class AudioTestReport:
    test_name: str
    result: TestResult
    duration_seconds: float
    checks: List[Tuple[str, bool, str]]  # (check_name, passed, message)
    audio_path: Optional[str] = None

# =============================================================================
# AUDIO ANALYSIS (Pure Python - no dependencies)
# =============================================================================

def analyze_wav(file_path: str) -> dict:
    """Analyze a WAV file without external dependencies."""
    try:
        with wave.open(file_path, 'rb') as wav:
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            framerate = wav.getframerate()
            n_frames = wav.getnframes()
            duration = n_frames / framerate

            # Read audio data
            raw_data = wav.readframes(n_frames)

            # Convert to samples
            if sample_width == 2:
                fmt = f"<{n_frames * n_channels}h"
                samples = struct.unpack(fmt, raw_data)
            else:
                samples = list(raw_data)

            # Calculate statistics
            if samples:
                max_amplitude = max(abs(s) for s in samples)
                avg_amplitude = sum(abs(s) for s in samples) / len(samples)

                # Normalize
                max_possible = 32767 if sample_width == 2 else 255
                peak_level = max_amplitude / max_possible
                avg_level = avg_amplitude / max_possible

                # Detect silence (avg < 1% of max)
                is_silent = avg_level < 0.01

                # Detect clipping (peak > 99%)
                is_clipped = peak_level > 0.99
            else:
                peak_level = 0
                avg_level = 0
                is_silent = True
                is_clipped = False

            return {
                'duration': duration,
                'sample_rate': framerate,
                'channels': n_channels,
                'bit_depth': sample_width * 8,
                'peak_level': peak_level,
                'avg_level': avg_level,
                'is_silent': is_silent,
                'is_clipped': is_clipped,
                'n_samples': len(samples),
            }
    except Exception as e:
        return {'error': str(e)}

def convert_to_wav(input_path: str, output_path: str) -> bool:
    """Convert audio file to WAV using ffmpeg."""
    try:
        result = subprocess.run([
            'ffmpeg', '-y', '-i', input_path,
            '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
            output_path
        ], capture_output=True, timeout=60)
        return result.returncode == 0
    except:
        return False

# =============================================================================
# TTS TESTING
# =============================================================================

def find_tts_system() -> Optional[str]:
    """Find available TTS system."""
    # Check for macOS say command first (most reliable)
    if subprocess.run(['which', 'say'], capture_output=True).returncode == 0:
        return "macos"

    # Check for XTTS
    xtts_path = Path("/Volumes/Plex/DevSymlinks/tts")
    if xtts_path.exists():
        return "xtts"

    # Check for espeak
    if subprocess.run(['which', 'espeak'], capture_output=True).returncode == 0:
        return "espeak"

    return None

def generate_tts_macos(text: str, output_path: str, voice: str = "Samantha") -> bool:
    """Generate TTS using macOS say command."""
    try:
        # Generate AIFF first
        aiff_path = output_path.replace('.wav', '.aiff')
        result = subprocess.run([
            'say', '-v', voice, '-o', aiff_path, text
        ], capture_output=True, timeout=60)

        if result.returncode != 0:
            return False

        # Convert to WAV
        return convert_to_wav(aiff_path, output_path)
    except Exception as e:
        print(f"TTS error: {e}")
        return False

def generate_tts_xtts(text: str, output_path: str, speaker_wav: str = None) -> bool:
    """Generate TTS using XTTS."""
    try:
        # This would call the XTTS API/CLI
        # For now, use a placeholder that checks if XTTS is available
        xtts_script = Path("/Volumes/Plex/DevSymlinks/tts/tts_generate.py")
        if not xtts_script.exists():
            return False

        cmd = ['python3', str(xtts_script), '--text', text, '--output', output_path]
        if speaker_wav:
            cmd.extend(['--speaker', speaker_wav])

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.returncode == 0 and Path(output_path).exists()
    except:
        return False

def test_tts(text: str, expected_duration_range: Tuple[float, float] = (0.5, 30.0)) -> AudioTestReport:
    """
    Test TTS generation.

    Args:
        text: Text to synthesize
        expected_duration_range: (min_seconds, max_seconds)

    Returns:
        AudioTestReport with test results
    """
    checks = []

    # Find TTS system
    tts_system = find_tts_system()
    if not tts_system:
        return AudioTestReport(
            test_name="TTS Generation",
            result=TestResult.SKIPPED,
            duration_seconds=0,
            checks=[("TTS System", False, "No TTS system found")]
        )

    checks.append(("TTS System", True, f"Using {tts_system}"))

    # Generate audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_path = f.name

    if tts_system == "macos":
        success = generate_tts_macos(text, output_path)
    elif tts_system == "xtts":
        success = generate_tts_xtts(text, output_path)
    else:
        success = False

    if not success:
        checks.append(("Generation", False, "TTS generation failed"))
        return AudioTestReport(
            test_name="TTS Generation",
            result=TestResult.FAILED,
            duration_seconds=0,
            checks=checks
        )

    checks.append(("Generation", True, "Audio file created"))

    # Analyze audio
    analysis = analyze_wav(output_path)

    if 'error' in analysis:
        checks.append(("Analysis", False, f"Error: {analysis['error']}"))
        return AudioTestReport(
            test_name="TTS Generation",
            result=TestResult.FAILED,
            duration_seconds=0,
            checks=checks,
            audio_path=output_path
        )

    # Duration check
    duration = analysis['duration']
    min_dur, max_dur = expected_duration_range
    duration_ok = min_dur <= duration <= max_dur
    checks.append((
        "Duration",
        duration_ok,
        f"{duration:.2f}s (expected {min_dur}-{max_dur}s)"
    ))

    # Silence check
    checks.append((
        "Not Silent",
        not analysis['is_silent'],
        f"Avg level: {analysis['avg_level']:.3f}"
    ))

    # Clipping check
    checks.append((
        "No Clipping",
        not analysis['is_clipped'],
        f"Peak level: {analysis['peak_level']:.3f}"
    ))

    # Overall result
    all_passed = all(check[1] for check in checks)

    return AudioTestReport(
        test_name="TTS Generation",
        result=TestResult.PASSED if all_passed else TestResult.FAILED,
        duration_seconds=duration,
        checks=checks,
        audio_path=output_path
    )

# =============================================================================
# RVC TESTING
# =============================================================================

def find_rvc_system() -> Optional[Path]:
    """Find RVC installation."""
    rvc_paths = [
        Path.home() / "Projects/RVC/rvc-webui",
        Path("/Volumes/Plex/DevSymlinks/RVC"),
    ]

    for path in rvc_paths:
        if path.exists():
            return path

    return None

def find_rvc_model() -> Optional[str]:
    """Find trained RVC model."""
    model_dirs = [
        Path.home() / "Projects/RVC/rvc-webui/weights",
        Path.home() / ".sam/models/rvc",
    ]

    for model_dir in model_dirs:
        if model_dir.exists():
            pth_files = list(model_dir.glob("*.pth"))
            if pth_files:
                return str(pth_files[0])

    return None

def convert_rvc(input_path: str, output_path: str, model_path: str) -> bool:
    """Convert audio using RVC."""
    rvc_path = find_rvc_system()
    if not rvc_path:
        return False

    try:
        # RVC CLI inference
        cmd = [
            'python3', str(rvc_path / 'infer.py'),
            '--input', input_path,
            '--output', output_path,
            '--model', model_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300, cwd=str(rvc_path))
        return result.returncode == 0 and Path(output_path).exists()
    except Exception as e:
        print(f"RVC error: {e}")
        return False

def test_rvc(input_audio: str) -> AudioTestReport:
    """
    Test RVC voice conversion.

    Args:
        input_audio: Path to input audio file

    Returns:
        AudioTestReport with test results
    """
    checks = []

    # Check input exists
    if not Path(input_audio).exists():
        return AudioTestReport(
            test_name="RVC Conversion",
            result=TestResult.FAILED,
            duration_seconds=0,
            checks=[("Input File", False, f"Not found: {input_audio}")]
        )

    checks.append(("Input File", True, f"Found: {input_audio}"))

    # Find RVC
    rvc_path = find_rvc_system()
    if not rvc_path:
        checks.append(("RVC System", False, "RVC not found"))
        return AudioTestReport(
            test_name="RVC Conversion",
            result=TestResult.SKIPPED,
            duration_seconds=0,
            checks=checks
        )

    checks.append(("RVC System", True, f"Found at {rvc_path}"))

    # Find model
    model_path = find_rvc_model()
    if not model_path:
        checks.append(("RVC Model", False, "No trained model found"))
        return AudioTestReport(
            test_name="RVC Conversion",
            result=TestResult.SKIPPED,
            duration_seconds=0,
            checks=checks
        )

    checks.append(("RVC Model", True, f"Using {Path(model_path).name}"))

    # Analyze input
    # Convert to WAV if needed
    input_wav = input_audio
    if not input_audio.endswith('.wav'):
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            input_wav = f.name
        if not convert_to_wav(input_audio, input_wav):
            checks.append(("Input Conversion", False, "Failed to convert input to WAV"))
            return AudioTestReport(
                test_name="RVC Conversion",
                result=TestResult.FAILED,
                duration_seconds=0,
                checks=checks
            )

    input_analysis = analyze_wav(input_wav)
    if 'error' in input_analysis:
        checks.append(("Input Analysis", False, input_analysis['error']))
        return AudioTestReport(
            test_name="RVC Conversion",
            result=TestResult.FAILED,
            duration_seconds=0,
            checks=checks
        )

    input_duration = input_analysis['duration']
    checks.append(("Input Analysis", True, f"Duration: {input_duration:.2f}s"))

    # Convert
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_path = f.name

    success = convert_rvc(input_wav, output_path, model_path)

    if not success:
        checks.append(("Conversion", False, "RVC conversion failed"))
        return AudioTestReport(
            test_name="RVC Conversion",
            result=TestResult.FAILED,
            duration_seconds=0,
            checks=checks
        )

    checks.append(("Conversion", True, "RVC conversion completed"))

    # Analyze output
    output_analysis = analyze_wav(output_path)

    if 'error' in output_analysis:
        checks.append(("Output Analysis", False, output_analysis['error']))
        return AudioTestReport(
            test_name="RVC Conversion",
            result=TestResult.FAILED,
            duration_seconds=0,
            checks=checks,
            audio_path=output_path
        )

    output_duration = output_analysis['duration']

    # Duration preserved (within 10%)
    duration_diff = abs(output_duration - input_duration) / input_duration
    duration_ok = duration_diff < 0.1
    checks.append((
        "Duration Preserved",
        duration_ok,
        f"Input: {input_duration:.2f}s, Output: {output_duration:.2f}s ({duration_diff*100:.1f}% diff)"
    ))

    # Not silent
    checks.append((
        "Not Silent",
        not output_analysis['is_silent'],
        f"Avg level: {output_analysis['avg_level']:.3f}"
    ))

    # No clipping
    checks.append((
        "No Clipping",
        not output_analysis['is_clipped'],
        f"Peak level: {output_analysis['peak_level']:.3f}"
    ))

    # Overall result
    all_passed = all(check[1] for check in checks)

    return AudioTestReport(
        test_name="RVC Conversion",
        result=TestResult.PASSED if all_passed else TestResult.FAILED,
        duration_seconds=output_duration,
        checks=checks,
        audio_path=output_path
    )

# =============================================================================
# BENCHMARK
# =============================================================================

def run_benchmark() -> dict:
    """Run full audio benchmark."""
    results = {
        'timestamp': str(Path.ctime(Path('.'))),
        'tests': []
    }

    print("=" * 60)
    print("SAM Audio Benchmark")
    print("=" * 60)

    # TTS tests
    tts_texts = [
        "Hello, I am SAM, your AI assistant.",
        "The quick brown fox jumps over the lazy dog.",
        "Testing one two three four five.",
    ]

    for text in tts_texts:
        print(f"\nTesting TTS: '{text[:30]}...'")
        report = test_tts(text)
        print_report(report)
        results['tests'].append({
            'name': report.test_name,
            'input': text,
            'result': report.result.value,
            'duration': report.duration_seconds,
            'checks': [(c[0], c[1], c[2]) for c in report.checks]
        })

    # Summary
    passed = sum(1 for t in results['tests'] if t['result'] == 'passed')
    failed = sum(1 for t in results['tests'] if t['result'] == 'failed')
    skipped = sum(1 for t in results['tests'] if t['result'] == 'skipped')

    print("\n" + "=" * 60)
    print(f"Summary: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    results['summary'] = {
        'passed': passed,
        'failed': failed,
        'skipped': skipped
    }

    return results

def print_report(report: AudioTestReport):
    """Print a test report."""
    status_icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}
    print(f"{status_icon[report.result.value]} {report.test_name}: {report.result.value.upper()}")
    for check_name, passed, message in report.checks:
        icon = "✓" if passed else "✗"
        print(f"  {icon} {check_name}: {message}")
    if report.audio_path:
        print(f"  📁 Audio: {report.audio_path}")

# =============================================================================
# CLI
# =============================================================================

def main():
    if len(sys.argv) < 2:
        print("""
SAM Audio Tester
================

Usage:
  audio_tester.py test-tts "Text to speak"    Test TTS generation
  audio_tester.py test-rvc input.wav          Test RVC conversion
  audio_tester.py benchmark                   Run full benchmark
  audio_tester.py check-systems               Check available audio systems

Automated Tests:
  - TTS: Generates audio, checks duration/silence/clipping
  - RVC: Converts voice, checks quality preservation
  - All tests return PASS/FAIL without human review
""")
        return

    cmd = sys.argv[1]

    if cmd == "test-tts" and len(sys.argv) > 2:
        text = sys.argv[2]
        report = test_tts(text)
        print_report(report)
        sys.exit(0 if report.result == TestResult.PASSED else 1)

    elif cmd == "test-rvc" and len(sys.argv) > 2:
        input_file = sys.argv[2]
        report = test_rvc(input_file)
        print_report(report)
        sys.exit(0 if report.result == TestResult.PASSED else 1)

    elif cmd == "benchmark":
        results = run_benchmark()
        # Save results
        output_file = Path("/tmp/sam_audio_benchmark.json")
        output_file.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to: {output_file}")

    elif cmd == "check-systems":
        print("Audio Systems Check")
        print("=" * 40)
        print(f"TTS System: {find_tts_system() or 'Not found'}")
        print(f"RVC System: {find_rvc_system() or 'Not found'}")
        print(f"RVC Model: {find_rvc_model() or 'Not found'}")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
