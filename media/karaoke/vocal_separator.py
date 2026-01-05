#!/usr/bin/env python3
"""
Vocal Separator using Demucs
Separates audio into stems: vocals, drums, bass, other

Uses Meta's Demucs AI model for high-quality separation.
"""

import subprocess
import argparse
import shutil
from pathlib import Path


def check_demucs():
    """Check if demucs is installed"""
    try:
        result = subprocess.run(['demucs', '--help'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def separate_vocals(input_file, output_dir=None, model='htdemucs', two_stems=True):
    """
    Separate vocals from a track using Demucs.

    Args:
        input_file: Path to audio file
        output_dir: Output directory (default: same as input)
        model: Demucs model to use
            - htdemucs: Hybrid Transformer (best quality)
            - htdemucs_ft: Fine-tuned version
            - mdx_extra: Older model, faster
        two_stems: If True, only output vocals/no_vocals (faster)

    Returns:
        dict with paths to output files
    """
    input_path = Path(input_file)
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = input_path.parent / 'separated'

    output_path.mkdir(parents=True, exist_ok=True)

    # Build demucs command
    cmd = ['demucs', '-n', model, '--out', str(output_path)]

    if two_stems:
        cmd.extend(['--two-stems', 'vocals'])

    cmd.append(str(input_path))

    print(f"Processing: {input_path.name}")
    print(f"Model: {model}")
    print(f"Output: {output_path}")
    print()

    # Run demucs
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None

    # Find output files
    # Demucs outputs to: output_dir/model_name/track_name/
    track_name = input_path.stem
    stems_dir = output_path / model / track_name

    if not stems_dir.exists():
        print(f"Output directory not found: {stems_dir}")
        return None

    outputs = {}
    for stem_file in stems_dir.iterdir():
        if stem_file.suffix == '.wav':
            stem_name = stem_file.stem
            outputs[stem_name] = stem_file
            print(f"  ✓ {stem_name}: {stem_file.name}")

    return outputs


def create_karaoke_track(vocals_path, no_vocals_path, output_path, vocal_level=-12):
    """
    Create a karaoke track with reduced (but not removed) vocals.

    This allows hearing the original melody while singing along.

    Args:
        vocals_path: Path to isolated vocals
        no_vocals_path: Path to instrumental/backing
        output_path: Output file path
        vocal_level: Vocal reduction in dB (more negative = quieter)
    """
    cmd = [
        'ffmpeg', '-y',
        '-i', str(no_vocals_path),
        '-i', str(vocals_path),
        '-filter_complex',
        f'[1:a]volume={vocal_level}dB[v];[0:a][v]amix=inputs=2:duration=longest',
        '-ac', '2',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Separate vocals from audio using Demucs')
    parser.add_argument('-i', '--input', required=True, help='Input audio file')
    parser.add_argument('-o', '--output', default=None, help='Output directory')
    parser.add_argument('-m', '--model', default='htdemucs',
                        choices=['htdemucs', 'htdemucs_ft', 'mdx_extra', 'mdx_extra_q'],
                        help='Demucs model to use')
    parser.add_argument('--full', action='store_true',
                        help='Output all 4 stems instead of just vocals/no_vocals')
    parser.add_argument('--karaoke', action='store_true',
                        help='Also create karaoke mix with reduced vocals')
    parser.add_argument('--vocal-level', type=float, default=-12,
                        help='Vocal level in dB for karaoke mix (default: -12)')
    args = parser.parse_args()

    if not check_demucs():
        print("Error: demucs not found")
        print("Install with: pip install demucs")
        return 1

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    print("=" * 60)
    print("  Demucs Vocal Separator")
    print("=" * 60)
    print()

    outputs = separate_vocals(
        input_path,
        args.output,
        model=args.model,
        two_stems=not args.full
    )

    if not outputs:
        return 1

    if args.karaoke and 'vocals' in outputs and 'no_vocals' in outputs:
        print()
        print("Creating karaoke mix...")
        karaoke_path = outputs['no_vocals'].parent / 'karaoke_mix.wav'
        if create_karaoke_track(outputs['vocals'], outputs['no_vocals'], karaoke_path, args.vocal_level):
            print(f"  ✓ karaoke_mix: {karaoke_path.name}")
            outputs['karaoke_mix'] = karaoke_path

    print()
    print("Done!")
    return 0


if __name__ == '__main__':
    exit(main())
