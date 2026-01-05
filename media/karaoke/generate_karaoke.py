#!/usr/bin/env python3
"""
SAM Karaoke Generator
Rivals Apple Music Sing by combining:
- AI vocal separation (Demucs)
- Synced lyrics (LRCLIB)
- Video generation with highlighting lyrics

Outputs karaoke videos compatible with Plex for Apple TV streaming.
"""

import subprocess
import argparse
import json
import tempfile
import shutil
from pathlib import Path
from vocal_separator import separate_vocals, check_demucs
from fetch_lyrics import LyricsLrclib, parse_lrc, lrc_to_ass


def get_audio_duration(audio_path):
    """Get audio duration in seconds using ffprobe"""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'json',
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    return None


def get_audio_metadata(audio_path):
    """Extract artist and title from audio file"""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-show_entries', 'format_tags=artist,title,album',
        '-of', 'json',
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        tags = data.get('format', {}).get('tags', {})
        return {
            'artist': tags.get('artist', tags.get('ARTIST', '')),
            'title': tags.get('title', tags.get('TITLE', '')),
            'album': tags.get('album', tags.get('ALBUM', ''))
        }
    return {'artist': '', 'title': '', 'album': ''}


def find_album_artwork(audio_path):
    """Look for album artwork near the audio file"""
    audio_dir = Path(audio_path).parent

    # Common artwork filenames
    artwork_names = [
        'cover.jpg', 'cover.png', 'Cover.jpg', 'Cover.png',
        'folder.jpg', 'folder.png', 'Folder.jpg', 'Folder.png',
        'artwork.jpg', 'artwork.png', 'Artwork.jpg', 'Artwork.png',
        'front.jpg', 'front.png', 'Front.jpg', 'Front.png',
        'album.jpg', 'album.png', 'Album.jpg', 'Album.png'
    ]

    for name in artwork_names:
        path = audio_dir / name
        if path.exists():
            return path

    # Look for any jpg/png
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        files = list(audio_dir.glob(ext))
        if files:
            return files[0]

    return None


def extract_embedded_artwork(audio_path, output_path):
    """Extract embedded album artwork from audio file"""
    cmd = [
        'ffmpeg', '-y', '-i', str(audio_path),
        '-an', '-vcodec', 'copy',
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and Path(output_path).exists():
        return output_path
    return None


def create_background_video(artwork_path, duration, output_path, resolution='1920x1080'):
    """
    Create background video from album artwork.

    Applies subtle Ken Burns effect for visual interest.
    """
    width, height = map(int, resolution.split('x'))

    if artwork_path:
        # Scale artwork and apply subtle zoom
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-i', str(artwork_path),
            '-t', str(duration),
            '-vf', (
                f'scale={width*1.1}:{height*1.1}:force_original_aspect_ratio=increase,'
                f'crop={width}:{height},'
                f'zoompan=z=\'min(zoom+0.0003,1.1)\':d={int(duration*30)}:x=\'iw/2-(iw/zoom/2)\':y=\'ih/2-(ih/zoom/2)\':s={resolution},'
                f'format=yuv420p'
            ),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            str(output_path)
        ]
    else:
        # Create gradient background if no artwork
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'color=c=0x1a1a2e:s={resolution}:d={duration}',
            '-vf', (
                f'drawtext=text=\'KARAOKE\':fontcolor=0x4a4a6a:fontsize=200:'
                f'x=(w-text_w)/2:y=(h-text_h)/2,'
                f'format=yuv420p'
            ),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            str(output_path)
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def create_karaoke_video(
    background_video,
    audio_path,
    subtitle_path,
    output_path,
    include_vocals=False,
    vocal_level=-12
):
    """
    Combine background, audio, and subtitles into final karaoke video.

    Args:
        background_video: Path to background video
        audio_path: Path to audio (instrumental or karaoke mix)
        subtitle_path: Path to ASS subtitle file
        output_path: Output path for final video
        include_vocals: Whether audio includes reduced vocals
        vocal_level: Vocal level if applicable
    """
    cmd = [
        'ffmpeg', '-y',
        '-i', str(background_video),
        '-i', str(audio_path),
        '-vf', f'ass={subtitle_path}',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '18',
        '-c:a', 'aac',
        '-b:a', '320k',
        '-movflags', '+faststart',
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def generate_karaoke(
    input_file,
    output_dir=None,
    artist=None,
    title=None,
    model='htdemucs',
    include_guide_vocals=True,
    vocal_level=-12,
    resolution='1920x1080',
    skip_separation=False
):
    """
    Generate a complete karaoke video.

    Args:
        input_file: Path to audio file
        output_dir: Output directory
        artist: Artist name (auto-detected if not provided)
        title: Track title (auto-detected if not provided)
        model: Demucs model for vocal separation
        include_guide_vocals: Include reduced vocals as guide
        vocal_level: dB level for guide vocals
        resolution: Output video resolution
        skip_separation: Skip vocal separation (use original audio)

    Returns:
        dict with paths to all output files
    """
    input_path = Path(input_file)

    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = input_path.parent / 'karaoke_output'

    output_path.mkdir(parents=True, exist_ok=True)

    # Get metadata
    meta = get_audio_metadata(input_path)
    if not artist:
        artist = meta['artist'] or input_path.stem.split(' - ')[0] if ' - ' in input_path.stem else 'Unknown'
    if not title:
        title = meta['title'] or input_path.stem.split(' - ')[-1] if ' - ' in input_path.stem else input_path.stem
    album = meta['album']

    print("=" * 60)
    print("  SAM Karaoke Generator")
    print("=" * 60)
    print()
    print(f"  Artist: {artist}")
    print(f"  Title:  {title}")
    if album:
        print(f"  Album:  {album}")
    print()

    outputs = {
        'artist': artist,
        'title': title,
        'album': album
    }

    # Get duration
    duration = get_audio_duration(input_path)
    if not duration:
        print("Error: Could not determine audio duration")
        return None

    print(f"  Duration: {int(duration // 60)}:{int(duration % 60):02d}")
    print()

    # Step 1: Fetch synced lyrics
    print("[1/4] Fetching synced lyrics...")

    fetcher = LyricsLrclib()
    result = fetcher.search(artist, title, album, int(duration))

    synced_lyrics = None
    if result:
        synced_lyrics = result.get('syncedLyrics')

    if synced_lyrics:
        print("      Found synced lyrics")

        # Save LRC file
        lrc_path = output_path / 'lyrics.lrc'
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write(synced_lyrics)
        outputs['lrc'] = lrc_path

        # Convert to ASS
        ass_path = output_path / 'lyrics.ass'
        lrc_to_ass(synced_lyrics, ass_path)
        outputs['ass'] = ass_path
        print(f"      Saved: {lrc_path.name}, {ass_path.name}")
    else:
        print("      No synced lyrics found")
        print("      Video will be generated without lyrics overlay")

    # Step 2: Vocal separation
    print()
    print("[2/4] Separating vocals...")

    if skip_separation:
        print("      Skipping (using original audio)")
        audio_for_video = input_path
        outputs['no_vocals'] = None
    else:
        if not check_demucs():
            print("      Error: Demucs not installed")
            print("      Install with: pip install demucs")
            return None

        stems = separate_vocals(input_path, output_path, model=model, two_stems=True)

        if not stems:
            print("      Vocal separation failed")
            return None

        outputs['vocals'] = stems.get('vocals')
        outputs['no_vocals'] = stems.get('no_vocals')

        if include_guide_vocals and 'vocals' in stems and 'no_vocals' in stems:
            # Create karaoke mix with reduced vocals
            print("      Creating karaoke mix with guide vocals...")
            from vocal_separator import create_karaoke_track

            karaoke_audio = output_path / 'karaoke_audio.wav'
            if create_karaoke_track(stems['vocals'], stems['no_vocals'], karaoke_audio, vocal_level):
                audio_for_video = karaoke_audio
                outputs['karaoke_audio'] = karaoke_audio
                print(f"      Guide vocals at {vocal_level}dB")
            else:
                audio_for_video = stems['no_vocals']
        else:
            audio_for_video = stems['no_vocals']

    # Step 3: Prepare background video
    print()
    print("[3/4] Creating background video...")

    # Find or extract artwork
    artwork = find_album_artwork(input_path)

    if not artwork:
        # Try to extract from audio file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_artwork = Path(tmp.name)
        artwork = extract_embedded_artwork(input_path, tmp_artwork)

    if artwork:
        print(f"      Using artwork: {Path(artwork).name}")
    else:
        print("      No artwork found, using gradient background")

    background_video = output_path / 'background.mp4'
    if create_background_video(artwork, duration, background_video, resolution):
        print(f"      Created: {background_video.name}")
    else:
        print("      Error creating background video")
        return None

    # Step 4: Generate final karaoke video
    print()
    print("[4/4] Generating karaoke video...")

    safe_name = f"{artist} - {title}".replace('/', '-').replace(':', '-')
    final_video = output_path / f'{safe_name} (Karaoke).mp4'

    if synced_lyrics:
        success = create_karaoke_video(
            background_video,
            audio_for_video,
            outputs['ass'],
            final_video
        )
    else:
        # No lyrics - just combine background and audio
        cmd = [
            'ffmpeg', '-y',
            '-i', str(background_video),
            '-i', str(audio_for_video),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '320k',
            '-movflags', '+faststart',
            str(final_video)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        success = result.returncode == 0

    if success:
        outputs['video'] = final_video
        print(f"      Created: {final_video.name}")
    else:
        print("      Error creating final video")
        return None

    # Also create instrumental-only version
    if outputs.get('no_vocals'):
        instrumental_video = output_path / f'{safe_name} (Instrumental).mp4'
        if synced_lyrics:
            create_karaoke_video(
                background_video,
                outputs['no_vocals'],
                outputs['ass'],
                instrumental_video
            )
        else:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(background_video),
                '-i', str(outputs['no_vocals']),
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '320k',
                str(instrumental_video)
            ]
            subprocess.run(cmd, capture_output=True, text=True)
        outputs['instrumental_video'] = instrumental_video
        print(f"      Created: {instrumental_video.name}")

    # Save metadata
    metadata_file = output_path / 'karaoke_info.json'
    meta_out = {
        'artist': artist,
        'title': title,
        'album': album,
        'duration': duration,
        'has_synced_lyrics': synced_lyrics is not None,
        'has_vocals_separated': not skip_separation,
        'guide_vocal_level': vocal_level if include_guide_vocals else None,
        'resolution': resolution
    }
    with open(metadata_file, 'w') as f:
        json.dump(meta_out, f, indent=2)

    # Cleanup temp files
    if background_video.exists():
        background_video.unlink()

    print()
    print("=" * 60)
    print("  Done!")
    print("=" * 60)
    print()
    print("  Output files:")
    print(f"    {final_video}")
    if outputs.get('instrumental_video'):
        print(f"    {outputs['instrumental_video']}")
    if outputs.get('lrc'):
        print(f"    {outputs['lrc']}")
    print()
    print("  Stream to Apple TV via Plex or AirPlay")
    print()

    return outputs


def batch_generate(input_dir, output_dir, **kwargs):
    """Generate karaoke for all audio files in a directory"""
    input_path = Path(input_dir)
    audio_extensions = {'.mp3', '.m4a', '.flac', '.wav', '.aac', '.ogg'}

    audio_files = [
        f for f in input_path.iterdir()
        if f.suffix.lower() in audio_extensions
    ]

    print(f"Found {len(audio_files)} audio files")

    results = []
    for i, audio_file in enumerate(audio_files, 1):
        print()
        print(f"[{i}/{len(audio_files)}] Processing: {audio_file.name}")
        print()

        try:
            result = generate_karaoke(audio_file, output_dir, **kwargs)
            if result:
                results.append(result)
        except Exception as e:
            print(f"Error: {e}")
            continue

    print()
    print(f"Successfully generated {len(results)}/{len(audio_files)} karaoke videos")
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Generate karaoke videos with AI vocal separation and synced lyrics'
    )
    parser.add_argument('-i', '--input', required=True,
                        help='Input audio file or directory')
    parser.add_argument('-o', '--output', default=None,
                        help='Output directory')
    parser.add_argument('-a', '--artist', default=None,
                        help='Artist name (auto-detected if not provided)')
    parser.add_argument('-t', '--title', default=None,
                        help='Track title (auto-detected if not provided)')
    parser.add_argument('-m', '--model', default='htdemucs',
                        choices=['htdemucs', 'htdemucs_ft', 'mdx_extra'],
                        help='Demucs model (default: htdemucs)')
    parser.add_argument('--no-guide', action='store_true',
                        help='Disable guide vocals (pure instrumental)')
    parser.add_argument('--vocal-level', type=float, default=-12,
                        help='Guide vocal level in dB (default: -12)')
    parser.add_argument('--resolution', default='1920x1080',
                        help='Video resolution (default: 1920x1080)')
    parser.add_argument('--skip-separation', action='store_true',
                        help='Skip vocal separation (use original audio)')
    parser.add_argument('--batch', action='store_true',
                        help='Process all audio files in input directory')
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Input not found: {input_path}")
        return 1

    kwargs = {
        'output_dir': args.output,
        'artist': args.artist,
        'title': args.title,
        'model': args.model,
        'include_guide_vocals': not args.no_guide,
        'vocal_level': args.vocal_level,
        'resolution': args.resolution,
        'skip_separation': args.skip_separation
    }

    if args.batch or input_path.is_dir():
        results = batch_generate(input_path, **kwargs)
        return 0 if results else 1
    else:
        result = generate_karaoke(input_path, **kwargs)
        return 0 if result else 1


if __name__ == '__main__':
    exit(main())
