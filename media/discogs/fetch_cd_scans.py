#!/usr/bin/env python3
"""
Discogs CD Scan Fetcher
Fetches CD scans, liner notes, and artwork from Discogs using exact catalog number matching.

Your folder naming scheme:
[Artist] - Year - Album - (Country - Label – Catalog#) - [Format]

This script parses the catalog number and finds the exact Discogs release for accurate scans.
"""

import os
import re
import json
import time
import requests
import argparse
from pathlib import Path
from urllib.parse import quote


class DiscogsScanner:
    """Fetch CD scans from Discogs using catalog number matching"""

    def __init__(self, token=None, output_dir=None):
        self.token = token or os.environ.get('DISCOGS_TOKEN')
        self.output_dir = Path(output_dir) if output_dir else Path('/Volumes/Music/_CD_Scans')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SAM-CDScanner/1.0 +https://github.com/SAM',
        })

        if self.token:
            self.session.headers['Authorization'] = f'Discogs token={self.token}'

        self.stats = {
            'processed': 0,
            'found': 0,
            'downloaded': 0,
            'not_found': 0,
            'errors': 0
        }

        # Rate limiting (Discogs allows 60 req/min authenticated, 25 unauthenticated)
        self.rate_limit = 0.5 if self.token else 2.5
        self.last_request = 0

    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def parse_folder_name(self, folder_name):
        """
        Parse album folder name to extract metadata.

        Format: [Artist] - Year - Album - (Country - Label – Catalog#) - [Format]
        Examples:
        - [Britney Spears] - 1999 - Baby One More Time - (Japan - Zomba - AVCZ-95114) - [ALAC]
        - [Air] - 1998 - Moon Safari - (France - Source - 7243 8 45185 2 8) - [FLAC]
        """
        # Main pattern
        pattern = r'\[(.+?)\]\s*-\s*(\d{4})\s*-\s*(.+?)\s*-\s*\(([^)]+)\)\s*-\s*\[([A-Z]+)\]'
        match = re.match(pattern, folder_name)

        if match:
            artist = match.group(1).strip()
            year = match.group(2)
            album = match.group(3).strip()
            release_info = match.group(4)
            format_type = match.group(5)

            # Parse release info: Country - Label – Catalog#
            # Note: Label uses em-dash (–), catalog may have hyphens
            # Pattern: Country - Label – Catalog# (where – is em-dash or en-dash)

            country = None
            label = None
            catalog = None

            # Try to split on em-dash or en-dash (– or —) for label/catalog separation
            # But only use regular hyphen/space for country
            release_match = re.match(r'^([^-–—]+?)\s*[-]\s*([^–—]+?)\s*[–—]\s*(.+)$', release_info)

            if release_match:
                # Full format: Country - Label – Catalog#
                country = release_match.group(1).strip()
                label = release_match.group(2).strip()
                catalog = release_match.group(3).strip()
            else:
                # Try simpler: Country - Label - Catalog# (last part is catalog)
                parts = re.split(r'\s*-\s*', release_info, maxsplit=2)
                if len(parts) >= 3:
                    country = parts[0].strip()
                    label = parts[1].strip()
                    catalog = parts[2].strip()
                elif len(parts) == 2:
                    label = parts[0].strip()
                    catalog = parts[1].strip()
                else:
                    catalog = release_info.strip()

            return {
                'artist': artist,
                'year': year,
                'album': album,
                'country': country,
                'label': label,
                'catalog': catalog,
                'format': format_type,
                'original': folder_name
            }

        # Fallback: simpler pattern without full metadata
        simple_pattern = r'\[(.+?)\]\s*-\s*(\d{4})\s*-\s*(.+?)(?:\s*-|$)'
        match = re.match(simple_pattern, folder_name)
        if match:
            return {
                'artist': match.group(1).strip(),
                'year': match.group(2),
                'album': match.group(3).strip(),
                'country': None,
                'label': None,
                'catalog': None,
                'format': None,
                'original': folder_name
            }

        return None

    def search_by_catalog(self, catalog, artist=None):
        """Search Discogs for a release by catalog number"""
        self._rate_limit()

        url = 'https://api.discogs.com/database/search'
        params = {
            'catno': catalog,
            'type': 'release'
        }

        if artist:
            params['artist'] = artist

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 401:
                print("  [!] Discogs token required for search")
                return None
            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get('results', [])

            if results:
                return results[0]  # Best match

            return None
        except Exception as e:
            print(f"  Search error: {e}")
            return None

    def search_fallback(self, artist, album, year=None):
        """Fallback search by artist and album name"""
        self._rate_limit()

        url = 'https://api.discogs.com/database/search'
        params = {
            'artist': artist,
            'release_title': album,
            'type': 'release'
        }

        if year:
            params['year'] = year

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code != 200:
                return None

            data = response.json()
            results = data.get('results', [])

            if results:
                return results[0]

            return None
        except Exception as e:
            return None

    def get_release_images(self, release_id):
        """Get all images for a specific release"""
        self._rate_limit()

        url = f'https://api.discogs.com/releases/{release_id}'

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return None, []

            data = response.json()
            images = data.get('images', [])

            # Get extra info
            extra_info = {
                'title': data.get('title'),
                'year': data.get('year'),
                'country': data.get('country'),
                'labels': [l.get('name') for l in data.get('labels', [])],
                'catno': [l.get('catno') for l in data.get('labels', [])],
                'formats': [f.get('name') for f in data.get('formats', [])],
                'tracklist': data.get('tracklist', []),
                'credits': data.get('extraartists', []),
                'notes': data.get('notes'),
                'uri': data.get('uri')
            }

            return extra_info, images
        except Exception as e:
            print(f"  Error getting release: {e}")
            return None, []

    def download_image(self, url, output_path):
        """Download an image"""
        self._rate_limit()

        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            pass
        return False

    def process_album_folder(self, folder_path, dry_run=False):
        """Process a single album folder"""
        folder_path = Path(folder_path)
        info = self.parse_folder_name(folder_path.name)

        if not info:
            return False

        artist = info['artist']
        album = info['album']
        catalog = info['catalog']
        year = info['year']
        country = info['country']

        print(f"\n[>] {artist} - {album}")
        if catalog:
            print(f"    Catalog: {catalog} ({country or 'Unknown'})")

        self.stats['processed'] += 1

        # Search strategy:
        # 1. Try catalog number first (most accurate)
        # 2. Fall back to artist + album

        result = None
        if catalog:
            result = self.search_by_catalog(catalog, artist)
            if result:
                print(f"    Found via catalog#: {result.get('title')}")

        if not result:
            result = self.search_fallback(artist, album, year)
            if result:
                print(f"    Found via search: {result.get('title')}")

        if not result:
            print(f"    Not found on Discogs")
            self.stats['not_found'] += 1
            return False

        self.stats['found'] += 1

        # Get release details and images
        release_id = result.get('id')
        extra_info, images = self.get_release_images(release_id)

        if not images:
            print(f"    No images available")
            return False

        # Create output directory for this album
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', f"{artist} - {album}")
        album_output = self.output_dir / safe_name

        print(f"    Found {len(images)} images")

        if dry_run:
            for i, img in enumerate(images):
                img_type = img.get('type', 'unknown')
                print(f"      [{i+1}] {img_type}: {img.get('width', '?')}x{img.get('height', '?')}")
            return True

        # Download images
        album_output.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(images):
            img_type = img.get('type', 'unknown')
            img_url = img.get('uri', img.get('resource_url'))

            if not img_url:
                continue

            # Determine filename based on type
            if img_type == 'primary':
                filename = 'cover.jpg'
            elif img_type == 'secondary':
                filename = f'back_{i:02d}.jpg'
            else:
                filename = f'{img_type}_{i:02d}.jpg'

            output_file = album_output / filename

            if output_file.exists():
                continue

            if self.download_image(img_url, output_file):
                self.stats['downloaded'] += 1
                print(f"      Downloaded: {filename}")

        # Save release info as JSON
        if extra_info:
            info_file = album_output / 'release_info.json'
            with open(info_file, 'w') as f:
                json.dump(extra_info, f, indent=2)

        return True

    def scan_library(self, library_path, dry_run=False, limit=0):
        """Scan entire music library for albums"""
        library = Path(library_path)

        # Find all album folders (pattern: [Artist] - Year - Album...)
        album_folders = []

        for root, dirs, files in os.walk(library):
            folder_name = Path(root).name
            if folder_name.startswith('[') and ' - ' in folder_name:
                # Check if it's actually an album folder (has audio files)
                has_audio = any(f.endswith(('.flac', '.m4a', '.mp3', '.alac')) for f in files)
                if has_audio:
                    album_folders.append(root)

        print(f"Found {len(album_folders)} album folders")

        if limit > 0:
            album_folders = album_folders[:limit]
            print(f"Processing first {limit}")

        for folder in album_folders:
            try:
                self.process_album_folder(folder, dry_run)
            except Exception as e:
                print(f"  Error: {e}")
                self.stats['errors'] += 1

        # Print summary
        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)
        print(f"  Processed:    {self.stats['processed']}")
        print(f"  Found:        {self.stats['found']}")
        print(f"  Not found:    {self.stats['not_found']}")
        if not dry_run:
            print(f"  Downloaded:   {self.stats['downloaded']}")
        print(f"  Errors:       {self.stats['errors']}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Fetch CD scans from Discogs')
    parser.add_argument('-l', '--library', default='/Volumes/Music/_Music Lossless',
                        help='Music library path')
    parser.add_argument('-o', '--output', default='/Volumes/Music/_CD_Scans',
                        help='Output directory for CD scans')
    parser.add_argument('-t', '--token', default=None,
                        help='Discogs API token (or set DISCOGS_TOKEN env var)')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of albums to process')
    parser.add_argument('--dry-run', action='store_true',
                        help='Only show what would be downloaded')
    parser.add_argument('--folder', type=str, default=None,
                        help='Process a single folder')
    args = parser.parse_args()

    print("=" * 60)
    print("  Discogs CD Scan Fetcher")
    print("  Using catalog number matching for accuracy")
    print("=" * 60)
    print()

    if not args.token and not os.environ.get('DISCOGS_TOKEN'):
        print("[!] Warning: No Discogs token provided")
        print("    Rate limited to 25 requests/minute")
        print("    Get a token at: https://www.discogs.com/settings/developers")
        print()

    scanner = DiscogsScanner(token=args.token, output_dir=args.output)

    if args.folder:
        scanner.process_album_folder(args.folder, args.dry_run)
    else:
        scanner.scan_library(args.library, args.dry_run, args.limit)


if __name__ == '__main__':
    main()
