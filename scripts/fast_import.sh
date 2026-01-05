#!/bin/bash
# Fast Beets Import Script
# Imports without slow MusicBrainz lookups - uses existing file metadata
# Run ftintitle and other fixes after import completes

set -e

QUARANTINE="/Volumes/Music/_Music Lossless/.quarantine"
LOG_FILE="/tmp/fast_import.log"

echo "=============================================="
echo "  Fast Beets Import"
echo "=============================================="
echo ""
echo "This imports using existing file tags (no MusicBrainz lookups)"
echo "Much faster - minutes instead of hours"
echo ""

# Count folders
TOTAL=$(ls -1 "$QUARANTINE" 2>/dev/null | wc -l | tr -d ' ')
echo "Folders to import: $TOTAL"
echo ""

# Disable slow plugins temporarily
echo "Temporarily disabling slow plugins..."
BEETS_CONFIG=~/.config/beets/config.yaml

# Backup config
cp "$BEETS_CONFIG" "${BEETS_CONFIG}.backup"

# Create fast import config
cat > /tmp/beets_fast_import.yaml << 'EOF'
# Fast import config - minimal plugins, no autotagging

directory: /Volumes/Music/_Music Lossless
library: /Users/davidquinton/.config/beets/library.db

import:
    move: no
    copy: no
    write: yes
    autotag: no           # Skip MusicBrainz lookups
    quiet: yes
    log: /tmp/fast_import.log
    duplicate_action: skip

# Minimal plugins for speed
plugins:
    - ftintitle           # Fix featured artists
    - duplicates

ftintitle:
    auto: yes
    drop: no
    format: 'feat. {0}'

paths:
    default: $albumartist/Albums/[$albumartist] - $year - $album - [$format]/$track - $title
    singleton: $artist/Singles/$title
    comp: Various Artists/$album/$track - $title
EOF

echo "Starting fast import..."
echo "Progress will be shown every 100 albums"
echo ""

# Run import with fast config
BEETSDIR=/tmp beet -c /tmp/beets_fast_import.yaml import -q "$QUARANTINE" 2>&1 | while read line; do
    echo "$line"
done &

IMPORT_PID=$!
echo "Import running with PID: $IMPORT_PID"
echo ""

# Monitor progress
while kill -0 $IMPORT_PID 2>/dev/null; do
    CURRENT=$(beet list -a 2>/dev/null | wc -l | tr -d ' ')
    IMPORTED=$((CURRENT - 163))  # Subtract already imported
    echo -ne "\rImported: $IMPORTED / $TOTAL albums"
    sleep 5
done

echo ""
echo ""
echo "Import complete!"
echo ""

# Restore original config
mv "${BEETS_CONFIG}.backup" "$BEETS_CONFIG"

# Show summary
echo "=============================================="
echo "  Summary"
echo "=============================================="
echo "Total albums now: $(beet list -a | wc -l)"
echo "Total tracks now: $(beet list | wc -l)"
echo ""
echo "Next steps:"
echo "  1. beet ftintitle    # Fix featured artists"
echo "  2. beet write        # Write tags to files"
echo "  3. Refresh Plex/Navidrome"
