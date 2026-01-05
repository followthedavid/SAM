#!/usr/bin/env python3
"""
LRCLIB Synced Lyrics Fetcher
Fetches word-synced and line-synced lyrics from LRCLIB
"""

import requests
import json
import re
import argparse
from pathlib import Path


class LyricsLrclib:
    """Fetch synced lyrics from LRCLIB"""

    BASE_URL = "https://lrclib.net/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SAM-Karaoke/1.0'
        })

    def search(self, artist, title, album=None, duration=None):
        """
        Search for synced lyrics.

        Args:
            artist: Artist name
            title: Track title
            album: Optional album name
            duration: Optional track duration in seconds

        Returns:
            dict with syncedLyrics, plainLyrics, etc.
        """
        url = f"{self.BASE_URL}/search"
        params = {
            'artist_name': artist,
            'track_name': title
        }

        if album:
            params['album_name'] = album
        if duration:
            params['duration'] = int(duration)

        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json()
                if results:
                    # Return best match (first result)
                    return results[0]
            return None
        except Exception as e:
            print(f"LRCLIB search error: {e}")
            return None

    def get_by_id(self, track_id):
        """Get lyrics by LRCLIB track ID"""
        url = f"{self.BASE_URL}/get/{track_id}"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"LRCLIB get error: {e}")
            return None

    def get_synced(self, artist, title, album=None, duration=None):
        """
        Get synced lyrics for a track.

        Returns:
            str: LRC formatted lyrics, or None if not found
        """
        result = self.search(artist, title, album, duration)
        if result:
            return result.get('syncedLyrics')
        return None

    def get_plain(self, artist, title, album=None):
        """Get plain (unsynced) lyrics"""
        result = self.search(artist, title, album)
        if result:
            return result.get('plainLyrics')
        return None


def parse_lrc(lrc_content):
    """
    Parse LRC file content into timed lines.

    Returns:
        list of (timestamp_ms, text)
    """
    lines = []

    for line in lrc_content.split('\n'):
        # Match [mm:ss.xx] text
        match = re.match(r'\[(\d+):(\d+)\.(\d+)\](.*)$', line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3))

            # Convert to milliseconds
            timestamp_ms = (minutes * 60 + seconds) * 1000 + centiseconds * 10

            text = match.group(4).strip()
            if text:  # Only add non-empty lines
                lines.append((timestamp_ms, text))

    return sorted(lines, key=lambda x: x[0])


def lrc_to_ass(lrc_content, output_path):
    """
    Convert LRC to ASS subtitle format for video overlay.

    ASS format allows for:
    - Karaoke highlighting
    - Custom styling
    - Position control
    """
    lines = parse_lrc(lrc_content)

    # ASS header
    ass_content = """[Script Info]
Title: Karaoke Lyrics
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000088FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,80,1
Style: Highlight,Arial,72,&H0088FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,50,50,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Convert lines to ASS dialogues
    for i, (start_ms, text) in enumerate(lines):
        # Calculate end time (next line start or +5 seconds)
        if i + 1 < len(lines):
            end_ms = lines[i + 1][0]
        else:
            end_ms = start_ms + 5000

        # Format timestamps as H:MM:SS.CC
        start_str = f"{start_ms // 3600000}:{(start_ms % 3600000) // 60000:02d}:{(start_ms % 60000) // 1000:02d}.{(start_ms % 1000) // 10:02d}"
        end_str = f"{end_ms // 3600000}:{(end_ms % 3600000) // 60000:02d}:{(end_ms % 60000) // 1000:02d}.{(end_ms % 1000) // 10:02d}"

        # Add dialogue line
        ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n"

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='Fetch synced lyrics from LRCLIB')
    parser.add_argument('-a', '--artist', required=True, help='Artist name')
    parser.add_argument('-t', '--title', required=True, help='Track title')
    parser.add_argument('-l', '--album', default=None, help='Album name')
    parser.add_argument('-d', '--duration', type=int, default=None, help='Track duration in seconds')
    parser.add_argument('-o', '--output', default=None, help='Output file path')
    parser.add_argument('--ass', action='store_true', help='Also output ASS subtitle format')
    args = parser.parse_args()

    fetcher = LyricsLrclib()

    print(f"Searching for: {args.artist} - {args.title}")

    result = fetcher.search(args.artist, args.title, args.album, args.duration)

    if not result:
        print("No lyrics found")
        return 1

    synced = result.get('syncedLyrics')
    plain = result.get('plainLyrics')

    if synced:
        print(f"✓ Found synced lyrics")
        output = args.output or f"{args.artist} - {args.title}.lrc"
        with open(output, 'w', encoding='utf-8') as f:
            f.write(synced)
        print(f"  Saved to: {output}")

        if args.ass:
            ass_output = Path(output).with_suffix('.ass')
            lrc_to_ass(synced, ass_output)
            print(f"  ASS saved to: {ass_output}")

    elif plain:
        print(f"✓ Found plain lyrics (not synced)")
        output = args.output or f"{args.artist} - {args.title}.txt"
        with open(output, 'w', encoding='utf-8') as f:
            f.write(plain)
        print(f"  Saved to: {output}")
    else:
        print("No lyrics in result")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
