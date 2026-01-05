#!/usr/bin/env python3
"""
Music Video Fetcher for SAM
Downloads official music videos from YouTube for your library.
Stores in Plex-compatible format for music video libraries.
"""

import subprocess
import json
import re
import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


class MusicVideoFetcher:
    """Fetch music videos from YouTube using yt-dlp"""

    def __init__(self, output_dir='/Volumes/Music/_Music_Videos'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stats = {
            'searched': 0,
            'downloaded': 0,
            'skipped': 0,
            'not_found': 0,
            'errors': 0
        }

        # Check for yt-dlp
        try:
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        except:
            print("ERROR: yt-dlp not found. Install with: brew install yt-dlp")
            raise

    def search_video(self, artist, title, official_only=True):
        """
        Search YouTube for a music video.
        Returns video URL if found.
        """
        # Build search query
        query = f"{artist} {title}"
        if official_only:
            query += " official music video"

        cmd = [
            'yt-dlp',
            '--default-search', 'ytsearch5',  # Search top 5 results
            '--dump-json',
            '--flat-playlist',
            '--no-download',
            query
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return None

            # Parse results
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    video = json.loads(line)
                    video_title = video.get('title', '').lower()
                    video_channel = video.get('channel', '').lower()

                    # Score the result
                    score = 0

                    # Artist name in title or channel
                    if artist.lower() in video_title or artist.lower() in video_channel:
                        score += 3

                    # Song title in video title
                    if title.lower() in video_title:
                        score += 3

                    # Official indicators
                    if 'official' in video_title:
                        score += 2
                    if 'vevo' in video_channel:
                        score += 2
                    if 'music video' in video_title:
                        score += 1

                    # Negative indicators
                    if 'cover' in video_title:
                        score -= 5
                    if 'karaoke' in video_title:
                        score -= 5
                    if 'lyrics' in video_title and 'video' not in video_title:
                        score -= 2
                    if 'live' in video_title:
                        score -= 1

                    if score >= 4:  # Good match threshold
                        return {
                            'url': video.get('url'),
                            'title': video.get('title'),
                            'channel': video.get('channel'),
                            'duration': video.get('duration'),
                            'score': score
                        }

                except json.JSONDecodeError:
                    continue

            return None

        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"  Search error: {e}")
            return None

    def download_video(self, video_info, artist, title, album=None):
        """Download a music video"""
        url = video_info['url']

        # Create artist directory
        safe_artist = re.sub(r'[<>:"/\\|?*]', '_', artist)
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)

        artist_dir = self.output_dir / safe_artist
        artist_dir.mkdir(exist_ok=True)

        output_file = artist_dir / f"{safe_artist} - {safe_title}.%(ext)s"

        # Check if already exists
        existing = list(artist_dir.glob(f"{safe_artist} - {safe_title}.*"))
        if existing:
            return 'skipped', existing[0]

        cmd = [
            'yt-dlp',
            '-f', 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            '--merge-output-format', 'mp4',
            '-o', str(output_file),
            '--embed-thumbnail',
            '--embed-metadata',
            '--no-playlist',
            f'https://www.youtube.com/watch?v={url}'
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                # Find the downloaded file
                downloaded = list(artist_dir.glob(f"{safe_artist} - {safe_title}.*"))
                if downloaded:
                    return 'downloaded', downloaded[0]
            return 'error', None
        except subprocess.TimeoutExpired:
            return 'timeout', None
        except Exception as e:
            return 'error', None

    def fetch_for_track(self, artist, title, album=None):
        """Search and download music video for a track"""
        self.stats['searched'] += 1

        # Search for video
        video = self.search_video(artist, title)

        if not video:
            self.stats['not_found'] += 1
            return None, 'not_found'

        # Download
        status, path = self.download_video(video, artist, title, album)

        if status == 'downloaded':
            self.stats['downloaded'] += 1
            return path, 'downloaded'
        elif status == 'skipped':
            self.stats['skipped'] += 1
            return path, 'skipped'
        else:
            self.stats['errors'] += 1
            return None, 'error'


def get_beets_tracks(artist_filter=None):
    """Get unique artist/title combinations from beets"""
    cmd = ['beet', 'list', '-f', '$artist|||$title|||$album']
    result = subprocess.run(cmd, capture_output=True, text=True)

    seen = set()
    tracks = []

    for line in result.stdout.strip().split('\n'):
        if not line or '|||' not in line:
            continue
        parts = line.split('|||')
        if len(parts) >= 3:
            artist = parts[0]
            title = parts[1]
            album = parts[2]

            # Filter by artist if specified
            if artist_filter and artist_filter.lower() not in artist.lower():
                continue

            # Deduplicate
            key = f"{artist.lower()}|{title.lower()}"
            if key in seen:
                continue
            seen.add(key)

            # Clean title (remove feat. etc for better search)
            clean_title = re.sub(r'\s*[\(\[].*[\)\]]', '', title)
            clean_title = re.sub(r'\s*feat\..*$', '', clean_title, flags=re.IGNORECASE)

            tracks.append({
                'artist': artist,
                'title': clean_title,
                'original_title': title,
                'album': album
            })

    return tracks


def main():
    parser = argparse.ArgumentParser(description='Fetch music videos from YouTube')
    parser.add_argument('-o', '--output', default='/Volumes/Music/_Music_Videos',
                        help='Output directory')
    parser.add_argument('--artist', type=str, help='Filter by artist')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of videos')
    parser.add_argument('--dry-run', action='store_true', help='Search only, no download')
    args = parser.parse_args()

    print("=" * 60)
    print("  SAM Music Video Fetcher")
    print("  Source: YouTube (official videos only)")
    print("=" * 60)
    print()

    fetcher = MusicVideoFetcher(output_dir=args.output)

    print("Loading tracks from beets...")
    tracks = get_beets_tracks(artist_filter=args.artist)
    print(f"Found {len(tracks)} unique tracks")

    if args.limit > 0:
        tracks = tracks[:args.limit]
        print(f"Limited to {args.limit} tracks")

    print()
    print(f"Output: {args.output}")
    print()

    for i, track in enumerate(tracks, 1):
        artist = track['artist']
        title = track['title']

        print(f"[{i}/{len(tracks)}] {artist} - {title}")

        if args.dry_run:
            video = fetcher.search_video(artist, title)
            if video:
                print(f"        Found: {video['title']} (score: {video['score']})")
            else:
                print(f"        Not found")
            time.sleep(1)
            continue

        path, status = fetcher.fetch_for_track(artist, title, track['album'])

        if status == 'downloaded':
            print(f"        Downloaded: {path.name}")
        elif status == 'skipped':
            print(f"        Skipped (exists)")
        elif status == 'not_found':
            print(f"        Not found")
        else:
            print(f"        Error")

        # Rate limiting
        time.sleep(2)

    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Searched:    {fetcher.stats['searched']}")
    print(f"  Downloaded:  {fetcher.stats['downloaded']}")
    print(f"  Skipped:     {fetcher.stats['skipped']}")
    print(f"  Not found:   {fetcher.stats['not_found']}")
    print(f"  Errors:      {fetcher.stats['errors']}")
    print()

    return 0


if __name__ == '__main__':
    exit(main())
