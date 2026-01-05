#!/usr/bin/env python3
"""
Bulk Apple Music Animated Artwork Fetcher
Fetches animated artwork for entire artist discographies from your beets library
"""

import subprocess
import requests
import re
import os
import sys
import json
import m3u8
import argparse
import time
from pathlib import Path
from sanitize_filename import sanitize as sanitize_filename
from mutagen.mp4 import MP4

class AppleMusicFetcher:
    def __init__(self, output_dir):
        self.session = requests.Session()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.token = None
        self._refresh_token()
        self.downloaded = set()  # Track what we've downloaded to avoid dupes

    def _refresh_token(self):
        """Get a fresh API token from Apple Music"""
        print("Getting Apple Music API token...")
        response = self.session.get("https://music.apple.com/us/album/positions-deluxe-edition/1553944254")
        jspath = re.search(r'crossorigin src="(/assets/index.+?\.js)"', response.text).group(1)
        response = self.session.get("https://music.apple.com" + jspath)
        self.token = re.search(r'(eyJhbGc.+?)"', response.text).group(1)
        self.session.headers.update({
            'authorization': f'Bearer {self.token}',
            'origin': 'https://music.apple.com'
        })
        print("Token acquired!\n")

    def search_artist(self, artist_name, country='us'):
        """Search Apple Music for an artist and return their ID"""
        url = f"https://amp-api.music.apple.com/v1/catalog/{country}/search"
        params = {
            'term': artist_name,
            'types': 'artists',
            'limit': 5
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 401:
                self._refresh_token()
                response = self.session.get(url, params=params, timeout=10)

            if response.status_code != 200:
                return None, None

            data = response.json()
            artists = data.get('results', {}).get('artists', {}).get('data', [])

            # Find best match - case insensitive
            for result in artists:
                attrs = result['attributes']
                if attrs['name'].lower() == artist_name.lower():
                    return result['id'], attrs['name']

            # Fall back to first result
            if artists:
                return artists[0]['id'], artists[0]['attributes']['name']

            return None, None
        except Exception as e:
            print(f"  Search error: {e}")
            return None, None

    def get_artist_albums(self, artist_id, country='us'):
        """Get all albums for an artist, checking for animated artwork"""
        albums_with_animation = []
        url = f"https://amp-api.music.apple.com/v1/catalog/{country}/artists/{artist_id}/albums"
        params = {'limit': 100, 'extend': 'editorialVideo'}

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 401:
                self._refresh_token()
                response = self.session.get(url, params=params, timeout=15)

            if response.status_code != 200:
                return []

            data = response.json()
            albums = data.get('data', [])

            seen_names = set()  # Avoid duplicate album names
            for album in albums:
                attrs = album['attributes']
                if 'editorialVideo' in attrs:
                    # Create a normalized key to avoid duplicates
                    key = f"{attrs['name'].lower()}_{attrs.get('releaseDate', '')[:4]}"
                    if key not in seen_names:
                        seen_names.add(key)
                        albums_with_animation.append({
                            'id': album['id'],
                            'data': {'data': [album]}  # Format for download_artwork
                        })

            return albums_with_animation
        except Exception as e:
            print(f"  Error getting albums: {e}")
            return []

    def download_artwork(self, album_data):
        """Download the animated artwork"""
        attrs = album_data['data'][0]['attributes']
        artist = attrs['artistName']
        album = attrs['name']
        year = attrs.get('releaseDate', '0000')[:4]

        fname = sanitize_filename(f"{artist} - {album} ({year}).mp4")

        # Track by normalized name to avoid downloading same content twice
        norm_key = f"{artist.lower()}|{album.lower()}|{year}"
        if norm_key in self.downloaded:
            return False

        output_path = self.output_dir / fname

        if output_path.exists():
            self.downloaded.add(norm_key)
            return False

        # Get m3u8 URL (prefer square)
        video_info = attrs['editorialVideo']
        m3u8_url = None
        for key in ['motionDetailSquare', 'motionSquareVideo1x1']:
            if key in video_info:
                m3u8_url = video_info[key].get('video')
                if m3u8_url:
                    break

        if not m3u8_url:
            return False

        try:
            # Parse m3u8 to find best quality
            playlist = m3u8.load(m3u8_url)

            # Find highest resolution HEVC stream
            best_stream = None
            best_resolution = 0

            for p in playlist.data['playlists']:
                stream_info = p['stream_info']
                codec = stream_info.get('codecs', '')[:4]
                resolution = stream_info.get('resolution', '0x0')
                width = int(resolution.split('x')[0]) if 'x' in str(resolution) else 0

                # Prefer HEVC (hvc1) at highest resolution
                if codec == 'hvc1' and width > best_resolution:
                    best_stream = p['uri']
                    best_resolution = width

            # Fallback to any highest res if no HEVC
            if not best_stream:
                for p in playlist.data['playlists']:
                    stream_info = p['stream_info']
                    resolution = stream_info.get('resolution', '0x0')
                    width = int(resolution.split('x')[0]) if 'x' in str(resolution) else 0
                    if width > best_resolution:
                        best_stream = p['uri']
                        best_resolution = width

            if not best_stream:
                return False

            # Download with ffmpeg
            temp_video = self.output_dir / "temp_video.mp4"
            result = subprocess.run(
                ['ffmpeg', '-loglevel', 'error', '-y', '-i', best_stream, '-c', 'copy', str(temp_video)],
                capture_output=True, text=True, timeout=120
            )

            if result.returncode != 0:
                return False

            # Move to final location
            temp_video.rename(output_path)

            # Tag the file
            self._tag_file(output_path, attrs)

            self.downloaded.add(norm_key)
            print(f"    Downloaded: {fname}")
            return True

        except Exception as e:
            print(f"    Download error: {e}")
            return False

    def _tag_file(self, path, attrs):
        """Add metadata tags to the video"""
        try:
            video = MP4(str(path))
            video["\xa9alb"] = attrs.get('name', '')
            video["aART"] = attrs.get('artistName', '')
            if 'url' in attrs:
                video["----:TXXX:URL"] = bytes(attrs['url'], 'UTF-8')
            if 'releaseDate' in attrs:
                video["----:TXXX:Release date"] = bytes(attrs['releaseDate'], 'UTF-8')
            if 'copyright' in attrs:
                video["cprt"] = attrs['copyright']
            if 'genreNames' in attrs and attrs['genreNames']:
                video["\xa9gen"] = attrs['genreNames'][0]
            video.pop("©too", None)
            video.save()
        except:
            pass


def get_beets_artists():
    """Get unique artists from beets library"""
    try:
        result = subprocess.run(
            ['beet', 'list', '-a', '-f', '$albumartist'],
            capture_output=True, text=True
        )

        artists = set()
        for line in result.stdout.strip().split('\n'):
            artist = line.strip()
            if artist:
                artists.add(artist)

        return sorted(artists)
    except Exception as e:
        print(f"Error getting beets artists: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Bulk download animated artwork from Apple Music')
    parser.add_argument('-o', '--output', default='/Volumes/Music/_Animated_Covers_Apple',
                        help='Output directory for animated artwork')
    parser.add_argument('-l', '--limit', type=int, default=0,
                        help='Limit number of artists to process (0 = no limit)')
    parser.add_argument('-a', '--artist', type=str, default=None,
                        help='Process a specific artist only')
    parser.add_argument('--dry-run', action='store_true',
                        help='Only check for animated artwork, do not download')
    args = parser.parse_args()

    print("=" * 60)
    print("  Apple Music Animated Artwork Bulk Fetcher")
    print("  (Full Discography Mode)")
    print("=" * 60)
    print()

    # Get artists from beets
    if args.artist:
        artists = [args.artist]
        print(f"Processing single artist: {args.artist}\n")
    else:
        print("Getting artists from beets library...")
        artists = get_beets_artists()
        print(f"Found {len(artists)} unique artists\n")

        if args.limit > 0:
            artists = artists[:args.limit]
            print(f"Processing first {args.limit} artists\n")

    # Initialize fetcher
    fetcher = AppleMusicFetcher(args.output)

    # Stats
    total_artists = len(artists)
    artists_found = 0
    albums_with_animation = 0
    downloaded = 0

    for i, artist in enumerate(artists, 1):
        print(f"[{i}/{total_artists}] {artist}")

        # Search Apple Music for artist
        artist_id, am_name = fetcher.search_artist(artist)
        if not artist_id:
            print("  Not found on Apple Music")
            continue

        artists_found += 1
        if am_name != artist:
            print(f"  Matched: {am_name}")

        # Get all albums with animated artwork
        animated_albums = fetcher.get_artist_albums(artist_id)
        if not animated_albums:
            print("  No animated artwork available")
            continue

        albums_with_animation += len(animated_albums)
        print(f"  Found {len(animated_albums)} albums with animated artwork")

        if not args.dry_run:
            for album_info in animated_albums:
                if fetcher.download_artwork(album_info['data']):
                    downloaded += 1
                time.sleep(0.5)  # Rate limiting

    # Summary
    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Total artists:           {total_artists}")
    print(f"  Found on Apple Music:    {artists_found}")
    print(f"  Albums with animation:   {albums_with_animation}")
    if not args.dry_run:
        print(f"  Downloaded:              {downloaded}")
    print(f"\n  Output directory: {args.output}")
    print()


if __name__ == '__main__':
    main()
