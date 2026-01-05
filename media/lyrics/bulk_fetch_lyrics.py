#!/usr/bin/env python3
"""
Bulk Synced Lyrics Fetcher for SAM
Fetches synced lyrics from LRCLIB for entire beets library.
Saves .lrc files alongside audio files for Plex/Navidrome.
"""

import subprocess
import requests
import json
import time
import argparse
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


class LyricsLrclib:
    """LRCLIB API client"""

    BASE_URL = "https://lrclib.net/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SAM-Lyrics/1.0 (+https://github.com/SAM)'
        })
        self.stats = {
            'searched': 0,
            'found_synced': 0,
            'found_plain': 0,
            'not_found': 0,
            'errors': 0,
            'skipped': 0
        }

    def search(self, artist, title, album=None, duration=None):
        """Search for synced lyrics"""
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
                    return results[0]
            return None
        except Exception as e:
            return None

    def get_synced(self, artist, title, album=None, duration=None):
        """Get synced lyrics, returns (synced_lyrics, plain_lyrics)"""
        result = self.search(artist, title, album, duration)
        if result:
            return result.get('syncedLyrics'), result.get('plainLyrics')
        return None, None


def parse_duration(duration_str):
    """Parse duration string (mm:ss or seconds) to seconds"""
    if not duration_str:
        return None
    try:
        if ':' in duration_str:
            parts = duration_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return float(duration_str)
    except:
        return None


def get_beets_tracks():
    """Get all tracks from beets library with metadata"""
    cmd = [
        'beet', 'list', '-f',
        '$path|||$artist|||$title|||$album|||$length'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    tracks = []
    for line in result.stdout.strip().split('\n'):
        if not line or '|||' not in line:
            continue
        parts = line.split('|||')
        if len(parts) >= 5:
            tracks.append({
                'path': parts[0],
                'artist': parts[1],
                'title': parts[2],
                'album': parts[3],
                'duration': parse_duration(parts[4]) if parts[4] else None
            })
    return tracks


def fetch_lyrics_for_track(fetcher, track, overwrite=False):
    """Fetch lyrics for a single track"""
    audio_path = Path(track['path'])
    lrc_path = audio_path.with_suffix('.lrc')
    txt_path = audio_path.with_suffix('.txt')

    # Skip if already exists
    if not overwrite and (lrc_path.exists() or txt_path.exists()):
        return 'skipped', track

    artist = track['artist']
    title = track['title']
    album = track['album']
    duration = track['duration']

    # Clean title (remove feat. for better matching)
    clean_title = re.sub(r'\s*[\(\[]?feat\.?.*$', '', title, flags=re.IGNORECASE)

    synced, plain = fetcher.get_synced(artist, clean_title, album, duration)

    if synced:
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write(synced)
        return 'synced', track
    elif plain:
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(plain)
        return 'plain', track
    else:
        return 'not_found', track


def bulk_fetch(tracks, max_workers=4, overwrite=False, limit=0):
    """Fetch lyrics for all tracks"""
    fetcher = LyricsLrclib()

    if limit > 0:
        tracks = tracks[:limit]

    print(f"Fetching lyrics for {len(tracks)} tracks...")
    print(f"Workers: {max_workers}")
    print()

    processed = 0

    # Rate limit: ~2 requests per second to be nice to LRCLIB
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}

        for track in tracks:
            future = executor.submit(fetch_lyrics_for_track, fetcher, track, overwrite)
            futures[future] = track
            time.sleep(0.5)  # Rate limiting

        for future in as_completed(futures):
            track = futures[future]
            try:
                result, _ = future.result()

                if result == 'synced':
                    fetcher.stats['found_synced'] += 1
                    print(f"  ✓ [synced] {track['artist']} - {track['title']}")
                elif result == 'plain':
                    fetcher.stats['found_plain'] += 1
                    print(f"  ○ [plain]  {track['artist']} - {track['title']}")
                elif result == 'skipped':
                    fetcher.stats['skipped'] += 1
                elif result == 'not_found':
                    fetcher.stats['not_found'] += 1

                processed += 1
                if processed % 100 == 0:
                    print(f"\n  Progress: {processed}/{len(tracks)}\n")

            except Exception as e:
                fetcher.stats['errors'] += 1

    return fetcher.stats


def main():
    parser = argparse.ArgumentParser(description='Bulk fetch synced lyrics from LRCLIB')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing lyrics')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of tracks')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--artist', type=str, help='Filter by artist')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fetched')
    args = parser.parse_args()

    print("=" * 60)
    print("  SAM Bulk Lyrics Fetcher")
    print("  Source: LRCLIB (free, open source)")
    print("=" * 60)
    print()

    print("Loading tracks from beets...")
    tracks = get_beets_tracks()
    print(f"Found {len(tracks)} tracks")

    if args.artist:
        tracks = [t for t in tracks if args.artist.lower() in t['artist'].lower()]
        print(f"Filtered to {len(tracks)} tracks by artist: {args.artist}")

    if args.dry_run:
        print("\nDry run - would fetch lyrics for:")
        for t in tracks[:20]:
            print(f"  {t['artist']} - {t['title']}")
        if len(tracks) > 20:
            print(f"  ... and {len(tracks) - 20} more")
        return 0

    print()
    stats = bulk_fetch(tracks, max_workers=args.workers, overwrite=args.overwrite, limit=args.limit)

    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Synced lyrics:  {stats['found_synced']}")
    print(f"  Plain lyrics:   {stats['found_plain']}")
    print(f"  Not found:      {stats['not_found']}")
    print(f"  Skipped:        {stats['skipped']}")
    print(f"  Errors:         {stats['errors']}")
    print()

    success_rate = (stats['found_synced'] + stats['found_plain']) / max(1, stats['found_synced'] + stats['found_plain'] + stats['not_found']) * 100
    print(f"  Success rate: {success_rate:.1f}%")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
