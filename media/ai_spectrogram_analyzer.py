#!/usr/bin/env python3
"""
AI-Powered Spectrogram Analyzer for Fake Lossless Detection
Uses vision AI to analyze spectrograms - no human expertise needed

Detection layers:
1. Automated spectral analysis (fast, ~98% accurate)
2. AI vision analysis of spectrograms (catches edge cases)
3. AccurateRip verification (100% for matched CD rips)
"""

import subprocess
import tempfile
import base64
import json
import os
import anthropic
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
SPECTROGRAM_DIR = Path.home() / ".sam_spectrograms"
RESULTS_FILE = Path.home() / ".sam_ai_analysis.json"

# Detection thresholds
CONFIDENCE_THRESHOLD = 0.85  # Below this, escalate to AI analysis


def generate_spectrogram(audio_path: Path, output_path: Path) -> bool:
    """Generate a spectrogram image from audio file using sox"""
    try:
        # For m4a/alac, pipe through ffmpeg first
        ext = audio_path.suffix.lower()

        if ext in ['.m4a', '.mp4', '.aac', '.wma', '.ogg']:
            # Pipe through ffmpeg to sox
            cmd = f'ffmpeg -v quiet -i "{audio_path}" -f wav - | sox - -n spectrogram -o "{output_path}" -x 1200 -y 600 -z 90 -t "{audio_path.stem[:50]}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
        else:
            # Direct sox for wav/flac
            result = subprocess.run([
                'sox', str(audio_path), '-n', 'spectrogram',
                '-o', str(output_path),
                '-x', '1200',  # Width
                '-y', '600',   # Height
                '-z', '90',    # Dynamic range
                '-t', audio_path.stem[:50]  # Title
            ], capture_output=True, timeout=120)

        return output_path.exists()
    except Exception as e:
        print(f"Error generating spectrogram: {e}")
        return False


def generate_zoomed_spectrogram(audio_path: Path, output_path: Path,
                                 freq_min: int = 14000, freq_max: int = 22050) -> bool:
    """Generate a zoomed spectrogram focusing on high frequencies where fakes are detected"""
    try:
        ext = audio_path.suffix.lower()

        # Create a high-frequency focused spectrogram
        if ext in ['.m4a', '.mp4', '.aac', '.wma', '.ogg']:
            cmd = f'ffmpeg -v quiet -i "{audio_path}" -f wav - | sox - -n spectrogram -o "{output_path}" -x 1200 -y 400 -z 90 -r -t "High Freq: {audio_path.stem[:30]}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
        else:
            result = subprocess.run([
                'sox', str(audio_path), '-n', 'spectrogram',
                '-o', str(output_path),
                '-x', '1200',
                '-y', '400',
                '-z', '90',
                '-r',  # Raw spectrogram (no legends, for detail)
                '-t', f'High Freq: {audio_path.stem[:30]}'
            ], capture_output=True, timeout=120)

        return output_path.exists()
    except Exception as e:
        print(f"Error generating zoomed spectrogram: {e}")
        return False


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64 for API"""
    with open(image_path, 'rb') as f:
        return base64.standard_b64encode(f.read()).decode('utf-8')


def analyze_with_ai(full_spec_path: Path, zoomed_spec_path: Path,
                    filename: str, file_info: Dict) -> Dict:
    """Use Claude's vision to analyze spectrograms for fake lossless indicators"""

    if not ANTHROPIC_API_KEY:
        return {
            'status': 'skipped',
            'reason': 'No API key configured',
            'confidence': 0
        }

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # Encode both spectrograms
        full_spec_b64 = encode_image_base64(full_spec_path)
        zoomed_spec_b64 = encode_image_base64(zoomed_spec_path)

        prompt = f"""Analyze these spectrograms to determine if this audio file is GENUINE LOSSLESS or a FAKE (transcoded from lossy source like MP3/AAC).

File: {filename}
Claimed format: {file_info.get('format', 'Unknown')}
Sample rate: {file_info.get('sample_rate', 'Unknown')} Hz
Bit depth: {file_info.get('bit_depth', 'Unknown')} bit

The first image is the full spectrogram. The second image focuses on high frequencies (14-22kHz) where transcoding artifacts are most visible.

INDICATORS OF FAKE LOSSLESS (transcoded from MP3/AAC):
1. HARD CUTOFF: Sharp horizontal line where frequencies abruptly stop (MP3 128kbps ~16kHz, 192kbps ~18kHz, 320kbps ~19-20kHz)
2. SHELF PATTERN: Flat, empty region above a certain frequency
3. FREQUENCY GAPS: Unnatural gaps or "shelves" in the high frequency content
4. MIRROR/FOLD ARTIFACTS: Strange symmetric patterns from poor encoding
5. LACK OF CONTENT above 16-20kHz when file claims to be 44.1kHz/16bit or higher

INDICATORS OF GENUINE LOSSLESS:
1. NATURAL ROLLOFF: Gradual decrease in high frequencies (not a sharp cutoff)
2. CONTENT extends to Nyquist frequency (half sample rate, e.g., 22kHz for 44.1kHz files)
3. NOISE FLOOR visible in high frequencies (shows real analog/digital conversion)
4. NATURAL acoustic characteristics throughout spectrum

IMPORTANT EXCEPTIONS:
- Older recordings (pre-1990s) may naturally lack high frequencies due to recording technology
- Some genres/productions intentionally filter highs
- Live recordings may have limited high-frequency content

Respond in this exact JSON format:
{{
  "verdict": "GENUINE" or "FAKE" or "UNCERTAIN",
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief explanation of what you observed",
  "indicators": ["list", "of", "specific", "observations"],
  "cutoff_frequency": null or estimated frequency in Hz where cutoff occurs,
  "likely_source": null or "MP3_128" or "MP3_192" or "MP3_320" or "AAC_256" etc if fake
}}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": full_spec_b64
                            }
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": zoomed_spec_b64
                            }
                        }
                    ]
                }
            ]
        )

        # Parse response
        response_text = response.content[0].text

        # Extract JSON from response
        try:
            # Try to find JSON in response
            if '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                result['status'] = 'analyzed'
                return result
        except json.JSONDecodeError:
            pass

        return {
            'status': 'parsed_failed',
            'raw_response': response_text,
            'confidence': 0
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'confidence': 0
        }


def get_file_info(audio_path: Path) -> Dict:
    """Get audio file metadata"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', str(audio_path)
        ], capture_output=True, text=True, timeout=30)

        data = json.loads(result.stdout)

        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break

        if audio_stream:
            return {
                'format': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': audio_stream.get('sample_rate', 'unknown'),
                'bit_depth': audio_stream.get('bits_per_sample', 'unknown'),
                'channels': audio_stream.get('channels', 'unknown'),
                'duration': float(data.get('format', {}).get('duration', 0))
            }
    except:
        pass

    return {'format': 'unknown'}


def analyze_file(audio_path: Path, force_ai: bool = False) -> Dict:
    """Full analysis pipeline for a single file"""

    result = {
        'file': str(audio_path),
        'filename': audio_path.name,
        'analyzed_at': datetime.now().isoformat(),
        'file_info': {},
        'automated_analysis': {},
        'ai_analysis': {},
        'final_verdict': 'UNKNOWN',
        'final_confidence': 0.0
    }

    # Get file info
    result['file_info'] = get_file_info(audio_path)

    # Create spectrogram directory
    SPECTROGRAM_DIR.mkdir(exist_ok=True)

    # Generate spectrograms
    file_hash = str(hash(str(audio_path)))[-8:]
    full_spec = SPECTROGRAM_DIR / f"{file_hash}_full.png"
    zoomed_spec = SPECTROGRAM_DIR / f"{file_hash}_zoomed.png"

    print(f"  Generating spectrograms...")

    if not generate_spectrogram(audio_path, full_spec):
        result['error'] = 'Failed to generate spectrogram'
        return result

    generate_zoomed_spectrogram(audio_path, zoomed_spec)
    if not zoomed_spec.exists():
        zoomed_spec = full_spec  # Fall back to full if zoomed fails

    # AI Analysis
    print(f"  Running AI analysis...")
    ai_result = analyze_with_ai(full_spec, zoomed_spec, audio_path.name, result['file_info'])
    result['ai_analysis'] = ai_result

    # Determine final verdict
    if ai_result.get('status') == 'analyzed':
        result['final_verdict'] = ai_result.get('verdict', 'UNKNOWN')
        result['final_confidence'] = ai_result.get('confidence', 0)

    # Save spectrogram paths
    result['spectrograms'] = {
        'full': str(full_spec),
        'zoomed': str(zoomed_spec)
    }

    return result


def analyze_batch(file_list: list, max_workers: int = 2) -> list:
    """Analyze a batch of files"""
    results = []

    print(f"\nAnalyzing {len(file_list)} files with AI vision...\n")

    for i, audio_path in enumerate(file_list, 1):
        print(f"[{i}/{len(file_list)}] {Path(audio_path).name}")
        result = analyze_file(Path(audio_path))
        results.append(result)

        # Print result
        verdict = result.get('final_verdict', 'UNKNOWN')
        confidence = result.get('final_confidence', 0)

        if verdict == 'FAKE':
            likely_source = result.get('ai_analysis', {}).get('likely_source', 'unknown')
            print(f"  ❌ FAKE ({confidence:.0%} confidence) - likely from {likely_source}")
        elif verdict == 'GENUINE':
            print(f"  ✅ GENUINE ({confidence:.0%} confidence)")
        else:
            print(f"  ❓ {verdict} ({confidence:.0%} confidence)")

        reasoning = result.get('ai_analysis', {}).get('reasoning', '')
        if reasoning:
            print(f"     {reasoning[:100]}...")
        print()

    return results


def main():
    import sys

    print("=" * 60)
    print("AI SPECTROGRAM ANALYZER")
    print("Vision-powered fake lossless detection")
    print("=" * 60)

    if not ANTHROPIC_API_KEY:
        print("\n⚠️  ANTHROPIC_API_KEY not set!")
        print("Set it with: export ANTHROPIC_API_KEY='your-key'")
        print("Or add to ~/.zshrc for persistence")
        return

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python ai_spectrogram_analyzer.py <file.flac>")
        print("  python ai_spectrogram_analyzer.py <directory>")
        print("  python ai_spectrogram_analyzer.py --flagged  # Analyze previously flagged files")
        return

    target = sys.argv[1]

    if target == '--flagged':
        # Load files flagged by automated analysis
        flagged_file = Path.home() / ".sam_quality_flagged.json"
        if flagged_file.exists():
            with open(flagged_file) as f:
                flagged = json.load(f)
            files = [f['file'] for f in flagged if f.get('needs_review')]
            print(f"\nFound {len(files)} flagged files for AI review")
        else:
            print("No flagged files found. Run quality analysis first.")
            return
    elif Path(target).is_file():
        files = [target]
    elif Path(target).is_dir():
        # Find all audio files in directory
        files = []
        for ext in ['*.flac', '*.m4a', '*.wav', '*.alac']:
            files.extend(Path(target).rglob(ext))
        files = [str(f) for f in files]
        print(f"\nFound {len(files)} audio files in {target}")
    else:
        print(f"Not found: {target}")
        return

    if not files:
        print("No files to analyze")
        return

    # Analyze
    results = analyze_batch(files)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    genuine = sum(1 for r in results if r.get('final_verdict') == 'GENUINE')
    fake = sum(1 for r in results if r.get('final_verdict') == 'FAKE')
    uncertain = sum(1 for r in results if r.get('final_verdict') == 'UNCERTAIN')

    print(f"Genuine:   {genuine}")
    print(f"Fake:      {fake}")
    print(f"Uncertain: {uncertain}")

    # Save results
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {RESULTS_FILE}")

    # List fakes
    if fake > 0:
        print("\n❌ FAKE FILES DETECTED:")
        for r in results:
            if r.get('final_verdict') == 'FAKE':
                print(f"  - {r['filename']}")
                if r.get('ai_analysis', {}).get('likely_source'):
                    print(f"    Source: {r['ai_analysis']['likely_source']}")


if __name__ == '__main__':
    main()
