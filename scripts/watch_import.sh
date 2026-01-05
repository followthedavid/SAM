#!/bin/bash
# Watch for import to complete, then run post-import tasks

echo "Watching for import to complete..."

while pgrep -f "beet import" > /dev/null; do
    ALBUMS=$(beet list -a | wc -l | tr -d ' ')
    TRACKS=$(beet list | wc -l | tr -d ' ')
    echo -ne "\rAlbums: $ALBUMS | Tracks: $TRACKS | Still importing..."
    sleep 10
done

echo ""
echo "Import complete! Starting post-import tasks..."
echo ""

/Users/davidquinton/ReverseLab/SAM/scripts/post_import.sh
