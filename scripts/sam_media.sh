#!/bin/bash
#
# SAM Media Capabilities CLI
# Unified interface for SAM's media management tools
#

set -e

SAM_ROOT="$HOME/ReverseLab/SAM"
MEDIA_ROOT="$SAM_ROOT/media"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                   SAM Media Capabilities                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: sam_media.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  artwork           Download animated album artwork from Apple Music"
    echo "  artwork-scan      Dry run - see what artwork is available"
    echo "  artwork-artist    Download artwork for a specific artist"
    echo "  status            Show current media collection status"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  sam_media.sh artwork                    # Full library scan and download"
    echo "  sam_media.sh artwork-scan               # Preview available artwork"
    echo "  sam_media.sh artwork-artist \"Beyoncé\"   # Single artist"
    echo "  sam_media.sh status                     # Collection statistics"
}

ensure_venv() {
    VENV_DIR="$MEDIA_ROOT/apple_music/venv"

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install -q -r "$MEDIA_ROOT/apple_music/requirements.txt"
    else
        source "$VENV_DIR/bin/activate"
    fi
}

cmd_artwork() {
    print_header
    echo -e "${GREEN}Downloading animated artwork from Apple Music...${NC}"
    echo ""

    ensure_venv
    cd "$MEDIA_ROOT/apple_music"
    python3 bulk_fetch.py "$@"
}

cmd_artwork_scan() {
    print_header
    echo -e "${YELLOW}Scanning for available animated artwork (dry run)...${NC}"
    echo ""

    ensure_venv
    cd "$MEDIA_ROOT/apple_music"
    python3 bulk_fetch.py --dry-run "$@"
}

cmd_artwork_artist() {
    if [ -z "$1" ]; then
        echo -e "${RED}Error: Artist name required${NC}"
        echo "Usage: sam_media.sh artwork-artist \"Artist Name\""
        exit 1
    fi

    print_header
    echo -e "${GREEN}Downloading artwork for: $1${NC}"
    echo ""

    ensure_venv
    cd "$MEDIA_ROOT/apple_music"
    python3 bulk_fetch.py --artist "$1"
}

cmd_status() {
    print_header
    echo -e "${BLUE}Media Collection Status${NC}"
    echo ""

    ARTWORK_DIR="/Volumes/Music/_Animated_Covers_Apple"

    if [ -d "$ARTWORK_DIR" ]; then
        COUNT=$(ls -1 "$ARTWORK_DIR"/*.mp4 2>/dev/null | wc -l | tr -d ' ')
        SIZE=$(du -sh "$ARTWORK_DIR" 2>/dev/null | cut -f1)

        echo "Apple Music Animated Artwork:"
        echo "  Location: $ARTWORK_DIR"
        echo "  Files:    $COUNT animations"
        echo "  Size:     $SIZE"
        echo ""

        echo "Top Artists:"
        ls "$ARTWORK_DIR"/*.mp4 2>/dev/null | sed 's/.*\///' | cut -d'-' -f1 | sort | uniq -c | sort -rn | head -10
    else
        echo "No artwork directory found at $ARTWORK_DIR"
    fi

    echo ""
    echo "Disk Space:"
    df -h /Volumes/Music 2>/dev/null | tail -1 | awk '{print "  Available: " $4 " of " $2}'

    echo ""
    echo "Beets Library:"
    ALBUMS=$(beet list -a 2>/dev/null | wc -l | tr -d ' ')
    TRACKS=$(beet list 2>/dev/null | wc -l | tr -d ' ')
    echo "  Albums: $ALBUMS"
    echo "  Tracks: $TRACKS"
}

# Main command dispatcher
case "${1:-help}" in
    artwork)
        shift
        cmd_artwork "$@"
        ;;
    artwork-scan)
        shift
        cmd_artwork_scan "$@"
        ;;
    artwork-artist)
        shift
        cmd_artwork_artist "$@"
        ;;
    status)
        cmd_status
        ;;
    help|--help|-h)
        print_header
        print_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
