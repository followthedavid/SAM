#!/bin/bash
# SAM Post-Import Script
# Runs all enrichment tasks after beets import completes

set -e

SAM_DIR="/Users/davidquinton/ReverseLab/SAM"
MEDIA_DIR="$SAM_DIR/media"
MUSIC_DIR="/Volumes/Music/_Music Lossless"

echo "=============================================="
echo "  SAM Post-Import Enrichment"
echo "=============================================="
echo ""
echo "Started: $(date)"
echo ""

# Activate SAM virtual environment
cd "$MEDIA_DIR"
source venv/bin/activate

# 1. Fix featured artists
echo "=== [1/6] Fixing featured artists ==="
beet ftintitle
echo "Done"
echo ""

# 2. Write tags to files
echo "=== [2/6] Writing tags to files ==="
beet write
echo "Done"
echo ""

# 3. Fetch synced lyrics
echo "=== [3/6] Fetching synced lyrics ==="
python3 lyrics/bulk_fetch_lyrics.py --workers 4
echo ""

# 4. Fetch CD scans from Discogs
echo "=== [4/6] Fetching CD scans ==="
export DISCOGS_TOKEN="ZVyTkhRtDtwJBXkoBDDJmmHcnpLdvuYlYzZCOLte"
python3 discogs/fetch_cd_scans.py
echo ""

# 5. Deploy animated covers
echo "=== [5/6] Deploying animated covers ==="
python3 apple_music/deploy_animated_covers.py
echo ""

# 6. Fetch music videos (limited to popular artists first)
echo "=== [6/6] Fetching music videos (top 50) ==="
python3 music_videos/fetch_music_videos.py --limit 50
echo ""

echo "=============================================="
echo "  Complete!"
echo "=============================================="
echo ""
echo "Finished: $(date)"
echo ""
echo "Summary:"
echo "  Albums: $(beet list -a | wc -l)"
echo "  Tracks: $(beet list | wc -l)"
echo "  Lyrics: $(find "$MUSIC_DIR" -name "*.lrc" | wc -l)"
echo "  CD Scans: $(ls /Volumes/Music/_CD_Scans 2>/dev/null | wc -l) albums"
echo "  Music Videos: $(ls /Volumes/Music/_Music_Videos/*/*.mp4 2>/dev/null | wc -l)"
echo ""
echo "Next: Refresh Plex and Navidrome libraries"
