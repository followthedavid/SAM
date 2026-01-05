#!/usr/bin/env python3
"""
Deploy Animated Covers to Music Library
Converts MP4 animated artwork to WebP/GIF and places in album folders for Navidrome/Plex
"""

import subprocess
import os
import sys
import argparse
from pathlib import Path
import json
import re

class AnimatedCoverDeployer:
    def __init__(self, source_dir, music_library, output_format='webp'):
        self.source_dir = Path(source_dir)
        self.music_library = Path(music_library)
        self.output_format = output_format
        self.matched = 0
        self.converted = 0
        self.skipped = 0
        self.not_found = 0

    def parse_filename(self, filename):
        """Extract artist and album from filename like 'Artist - Album (Year).mp4'"""
        # Remove extension
        name = filename.rsplit('.', 1)[0]

        # Try to match "Artist - Album (Year)" pattern
        match = re.match(r'^(.+?) - (.+?) \((\d{4})\)$', name)
        if match:
            return {
                'artist': match.group(1).strip(),
                'album': match.group(2).strip(),
                'year': match.group(3)
            }

        # Fallback: split on " - "
        if ' - ' in name:
            parts = name.split(' - ', 1)
            album_part = parts[1]
            # Try to extract year from album part
            year_match = re.search(r'\((\d{4})\)', album_part)
            year = year_match.group(1) if year_match else None
            album = re.sub(r'\s*\(\d{4}\)\s*$', '', album_part)
            return {
                'artist': parts[0].strip(),
                'album': album.strip(),
                'year': year
            }

        return None

    def normalize_name(self, name):
        """Normalize a name for matching"""
        if not name:
            return ''
        # Lowercase, remove special characters, collapse whitespace
        name = name.lower()
        # Remove common suffixes
        name = re.sub(r'\s*\(deluxe.*?\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\(remaster.*?\)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\[.*?\]', '', name)
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def fuzzy_match(self, s1, s2):
        """Check if two strings are fuzzy matches"""
        n1 = self.normalize_name(s1)
        n2 = self.normalize_name(s2)

        # Exact match
        if n1 == n2:
            return True

        # One contains the other
        if n1 in n2 or n2 in n1:
            return True

        # Check word overlap
        words1 = set(n1.split())
        words2 = set(n2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / min(len(words1), len(words2))
            if overlap >= 0.6:
                return True

        return False

    def find_album_folder(self, artist, album, year=None):
        """Find the matching album folder in the music library"""
        matches = []

        # Walk through library looking for matching folders
        for root, dirs, files in os.walk(self.music_library):
            root_path = Path(root)
            depth = len(root_path.relative_to(self.music_library).parts)

            # Don't go too deep
            if depth > 4:
                continue

            # Check current folder name
            folder_name = root_path.name

            # Skip non-album folders
            if folder_name in ['Singles', 'EPs', 'Extras', 'Videos', 'Tracks', '_Singles', '_EPs']:
                continue

            # Look for pattern like [Artist] - Year - Album or just album name
            # Pattern 1: [Artist] - Year - Album - (Label) - [Format]
            folder_match = re.match(r'\[(.+?)\]\s*-\s*(\d{4})\s*-\s*(.+?)(?:\s*-\s*\(|$)', folder_name)

            if folder_match:
                folder_artist = folder_match.group(1)
                folder_year = folder_match.group(2)
                folder_album = folder_match.group(3).strip()

                # Check if matches
                if self.fuzzy_match(artist, folder_artist) and self.fuzzy_match(album, folder_album):
                    # Year match is bonus
                    score = 2
                    if year and folder_year == year:
                        score = 3
                    matches.append((score, root_path))
            else:
                # Pattern 2: Just check if folder contains artist and album
                if self.fuzzy_match(artist, folder_name) or self.fuzzy_match(album, folder_name):
                    # Check parent for artist
                    parent_name = root_path.parent.name if root_path.parent else ''
                    if self.fuzzy_match(artist, parent_name) and self.fuzzy_match(album, folder_name):
                        matches.append((1, root_path))

        # Return best match
        if matches:
            matches.sort(key=lambda x: -x[0])
            return matches[0][1]

        return None

    def convert_to_animated(self, source_mp4, output_path):
        """Convert MP4 to animated WebP or GIF"""
        try:
            if self.output_format == 'webp':
                # Animated WebP - good quality, small size
                cmd = [
                    'ffmpeg', '-y', '-i', str(source_mp4),
                    '-vf', 'scale=600:-1,fps=15',
                    '-t', '8',  # 8 seconds
                    '-loop', '0',
                    '-quality', '75',
                    '-lossless', '0',
                    str(output_path)
                ]
            else:  # gif
                # Animated GIF with palette optimization
                cmd = [
                    'ffmpeg', '-y', '-i', str(source_mp4),
                    '-vf', 'scale=400:-1,fps=12,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer',
                    '-t', '6',
                    str(output_path)
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception as e:
            print(f"    Conversion error: {e}")
            return False

    def deploy(self, dry_run=False):
        """Deploy all animated covers"""
        print("=" * 60)
        print("  Animated Cover Deployment")
        print("=" * 60)
        print(f"\nSource: {self.source_dir}")
        print(f"Library: {self.music_library}")
        print(f"Format: {self.output_format}")
        print(f"Dry run: {dry_run}\n")

        # Get all MP4 files
        mp4_files = list(self.source_dir.glob('*.mp4'))
        # Filter out test files
        mp4_files = [f for f in mp4_files if not f.name.startswith('test_')]
        print(f"Found {len(mp4_files)} animated covers\n")

        for mp4_file in mp4_files:
            info = self.parse_filename(mp4_file.name)
            if not info:
                print(f"[?] Could not parse: {mp4_file.name}")
                self.skipped += 1
                continue

            artist = info['artist']
            album = info['album']
            year = info.get('year')
            print(f"[>] {artist} - {album}" + (f" ({year})" if year else ""))

            # Find matching album folder
            album_folder = self.find_album_folder(artist, album, year)
            if not album_folder:
                print(f"    Not found in library")
                self.not_found += 1
                continue

            self.matched += 1
            output_file = album_folder / f"cover.{self.output_format}"

            # Check if already exists
            if output_file.exists():
                print(f"    Already exists")
                self.skipped += 1
                continue

            # Show relative path
            try:
                rel_path = album_folder.relative_to(self.music_library)
            except ValueError:
                rel_path = album_folder.name
            print(f"    -> {rel_path}/cover.{self.output_format}")

            if not dry_run:
                if self.convert_to_animated(mp4_file, output_file):
                    self.converted += 1
                    size = output_file.stat().st_size / 1024
                    print(f"    Converted ({size:.0f}KB)")
                else:
                    print(f"    Failed to convert")

        # Summary
        print("\n" + "=" * 60)
        print("  Summary")
        print("=" * 60)
        print(f"  Total MP4 files:     {len(mp4_files)}")
        print(f"  Matched to library:  {self.matched}")
        print(f"  Not found:           {self.not_found}")
        print(f"  Skipped (exists):    {self.skipped}")
        if not dry_run:
            print(f"  Converted:           {self.converted}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Deploy animated covers to music library')
    parser.add_argument('-s', '--source', default='/Volumes/Music/_Animated_Covers_Apple',
                        help='Source directory with MP4 artwork')
    parser.add_argument('-l', '--library', default='/Volumes/Music/_Music Lossless',
                        help='Music library directory')
    parser.add_argument('-f', '--format', choices=['webp', 'gif'], default='webp',
                        help='Output format (webp or gif)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview only, do not convert')
    args = parser.parse_args()

    deployer = AnimatedCoverDeployer(args.source, args.library, args.format)
    deployer.deploy(args.dry_run)


if __name__ == '__main__':
    main()
