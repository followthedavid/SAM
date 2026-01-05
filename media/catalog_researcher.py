#!/usr/bin/env python3
"""
Catalog Number Researcher for SAM
Searches MusicBrainz for missing catalog numbers with confidence scoring.

Matching criteria:
- Artist name match
- Album name match
- Track count match
- Track duration similarity
- Country/Label info
"""

import subprocess
import requests
import time
import json
import re
from difflib import SequenceMatcher

class CatalogResearcher:
    """Research missing catalog numbers via MusicBrainz"""

    MB_API = "https://musicbrainz.org/ws/2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SAM-CatalogResearcher/1.0 (https://github.com/SAM)'
        })
        self.rate_limit = 1.0  # MusicBrainz allows 1 req/sec
        self.last_request = 0

    def _wait_rate_limit(self):
        """Respect MusicBrainz rate limits"""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def _similarity(self, a, b):
        """Calculate string similarity (0-1)"""
        if not a or not b:
            return 0
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def search_releases(self, artist, album):
        """Search MusicBrainz for releases matching artist/album"""
        self._wait_rate_limit()

        query = f'artist:"{artist}" AND release:"{album}"'
        url = f"{self.MB_API}/release"
        params = {
            'query': query,
            'fmt': 'json',
            'limit': 10
        }

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json().get('releases', [])
        except Exception as e:
            print(f"  Error searching: {e}")
        return []

    def get_release_details(self, release_id):
        """Get full release details including tracks"""
        self._wait_rate_limit()

        url = f"{self.MB_API}/release/{release_id}"
        params = {
            'fmt': 'json',
            'inc': 'recordings+labels+release-groups'
        }

        try:
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"  Error getting details: {e}")
        return None

    def calculate_confidence(self, local_album, mb_release, mb_details=None):
        """
        Calculate confidence score (0-100) for a match

        Factors:
        - Artist name similarity (25%)
        - Album name similarity (25%)
        - Track count match (20%)
        - Track duration similarity (20%)
        - Has catalog number (10%)
        """
        score = 0
        breakdown = {}

        # Artist similarity (25 points)
        mb_artist = mb_release.get('artist-credit', [{}])[0].get('name', '')
        artist_sim = self._similarity(local_album['albumartist'], mb_artist)
        breakdown['artist'] = artist_sim * 25
        score += breakdown['artist']

        # Album similarity (25 points)
        album_sim = self._similarity(local_album['album'], mb_release.get('title', ''))
        breakdown['album'] = album_sim * 25
        score += breakdown['album']

        # Track count (20 points)
        mb_track_count = mb_release.get('track-count', 0)
        if mb_track_count == local_album['track_count']:
            breakdown['tracks'] = 20
        elif abs(mb_track_count - local_album['track_count']) <= 2:
            breakdown['tracks'] = 10
        else:
            breakdown['tracks'] = 0
        score += breakdown['tracks']

        # Catalog number presence (10 points)
        label_info = mb_release.get('label-info', [])
        has_catno = any(li.get('catalog-number') for li in label_info)
        breakdown['has_catalog'] = 10 if has_catno else 0
        score += breakdown['has_catalog']

        # Duration similarity (20 points) - if we have details
        if mb_details and 'media' in mb_details:
            mb_durations = []
            for media in mb_details.get('media', []):
                for track in media.get('tracks', []):
                    if track.get('recording', {}).get('length'):
                        mb_durations.append(track['recording']['length'] / 1000)

            if mb_durations and local_album.get('durations'):
                # Compare total duration
                mb_total = sum(mb_durations)
                local_total = sum(local_album['durations'])
                if local_total > 0:
                    duration_diff = abs(mb_total - local_total) / local_total
                    if duration_diff < 0.02:  # Within 2%
                        breakdown['duration'] = 20
                    elif duration_diff < 0.05:  # Within 5%
                        breakdown['duration'] = 15
                    elif duration_diff < 0.10:  # Within 10%
                        breakdown['duration'] = 10
                    else:
                        breakdown['duration'] = 0
                else:
                    breakdown['duration'] = 0
            else:
                breakdown['duration'] = 10  # Neutral if can't compare
        else:
            breakdown['duration'] = 10  # Neutral

        score += breakdown.get('duration', 0)

        return round(score, 1), breakdown

    def extract_catalog_info(self, mb_release):
        """Extract catalog number, label, country from release"""
        label_info = mb_release.get('label-info', [])

        catalog_num = None
        label = None

        for li in label_info:
            if li.get('catalog-number'):
                catalog_num = li['catalog-number']
                if li.get('label', {}).get('name'):
                    label = li['label']['name']
                break

        country = mb_release.get('country', '')

        return {
            'catalog_number': catalog_num,
            'label': label,
            'country': country,
            'year': mb_release.get('date', '')[:4] if mb_release.get('date') else '',
            'format': mb_release.get('media', [{}])[0].get('format', '') if mb_release.get('media') else ''
        }

    def research_album(self, album_info):
        """
        Research a single album, return best matches with confidence

        Returns list of (confidence, catalog_info, mb_release) tuples
        """
        results = []

        releases = self.search_releases(
            album_info['albumartist'],
            album_info['album']
        )

        for release in releases:
            # Get details for better matching
            details = self.get_release_details(release['id'])

            confidence, breakdown = self.calculate_confidence(
                album_info, release, details
            )

            catalog_info = self.extract_catalog_info(release)

            if catalog_info['catalog_number']:  # Only include if has catalog #
                results.append({
                    'confidence': confidence,
                    'breakdown': breakdown,
                    'catalog': catalog_info,
                    'mb_id': release['id'],
                    'mb_title': release.get('title', ''),
                    'mb_artist': release.get('artist-credit', [{}])[0].get('name', '')
                })

        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:5]  # Top 5 matches


def get_albums_missing_catalog():
    """Get albums from beets that are missing catalog numbers"""
    result = subprocess.run(
        ['beet', 'list', '-a', '-f', '$id|||$albumartist|||$album|||$country|||$label'],
        capture_output=True, text=True
    )

    albums = []
    for line in result.stdout.strip().split('\n'):
        if '|||' in line:
            parts = line.split('|||')
            if len(parts) >= 3:
                albums.append({
                    'id': parts[0],
                    'albumartist': parts[1],
                    'album': parts[2],
                    'country': parts[3] if len(parts) > 3 else '',
                    'label': parts[4] if len(parts) > 4 else ''
                })

    # Now check which ones are missing catalog numbers
    result2 = subprocess.run(
        ['beet', 'list', '-a', '-f', '$id|||$catalognum', 'catalognum::^$'],
        capture_output=True, text=True
    )

    missing_ids = set()
    for line in result2.stdout.strip().split('\n'):
        if '|||' in line:
            album_id = line.split('|||')[0]
            missing_ids.add(album_id)

    # Filter to only missing
    missing_albums = [a for a in albums if a['id'] in missing_ids]

    # Get track counts and durations
    for album in missing_albums:
        result3 = subprocess.run(
            ['beet', 'list', '-f', '$length', f'album_id:{album["id"]}'],
            capture_output=True, text=True
        )
        durations = []
        for line in result3.stdout.strip().split('\n'):
            if line:
                try:
                    # Parse duration like "3:45" to seconds
                    parts = line.split(':')
                    if len(parts) == 2:
                        durations.append(int(parts[0]) * 60 + int(parts[1]))
                except:
                    pass
        album['durations'] = durations
        album['track_count'] = len(durations) if durations else 0

    return missing_albums


def main():
    print("=" * 60)
    print("CATALOG NUMBER RESEARCHER")
    print("=" * 60)
    print()

    researcher = CatalogResearcher()

    print("Finding albums missing catalog numbers...")
    missing = get_albums_missing_catalog()
    print(f"Found {len(missing)} albums without catalog numbers\n")

    results_file = '/tmp/catalog_research_results.json'
    all_results = []

    for i, album in enumerate(missing[:50], 1):  # Process first 50
        print(f"[{i}/{min(50, len(missing))}] {album['albumartist']} - {album['album']}")

        matches = researcher.research_album(album)

        if matches:
            best = matches[0]
            print(f"  Best match: {best['confidence']}% - {best['catalog']['catalog_number']} ({best['catalog']['country']} - {best['catalog']['label']})")

            all_results.append({
                'album': album,
                'matches': matches
            })
        else:
            print("  No matches found")

        print()

    # Save results
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")
    print("\nHigh confidence matches (>80%):")
    for r in all_results:
        if r['matches'] and r['matches'][0]['confidence'] >= 80:
            m = r['matches'][0]
            print(f"  {r['album']['albumartist']} - {r['album']['album']}")
            print(f"    -> {m['catalog']['catalog_number']} ({m['catalog']['country']}) [{m['confidence']}%]")


if __name__ == '__main__':
    main()
