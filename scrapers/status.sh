#!/bin/bash
# Quick status check for all scrapers

echo "========================================"
echo "  SAM Training Data Collection Status"
echo "  $(date)"
echo "========================================"
echo ""

echo "🔄 RUNNING SCRAPERS:"
ps aux | grep -E 'ripper.py' | grep -v grep | awk '{print "  •", $NF}' | sed 's/\.py.*//'
RUNNING=$(ps aux | grep -E 'ripper.py' | grep -v grep | wc -l | tr -d ' ')
echo "  Total: $RUNNING running"
echo ""

echo "📊 DATABASE STATS:"

# Nifty
if [ -f "/Volumes/David External/nifty_archive/stories.db" ]; then
    NIFTY_IDX=$(sqlite3 "/Volumes/David External/nifty_archive/stories.db" "SELECT COUNT(*) FROM stories" 2>/dev/null || echo "0")
    NIFTY_DL=$(sqlite3 "/Volumes/David External/nifty_archive/stories.db" "SELECT COUNT(*) FROM stories WHERE downloaded=1" 2>/dev/null || echo "0")
    echo "  Nifty:        $NIFTY_DL / $NIFTY_IDX downloaded"
fi

# AO3
if [ -f "/Volumes/David External/ao3_roleplay/stories.db" ]; then
    AO3_IDX=$(sqlite3 "/Volumes/David External/ao3_roleplay/stories.db" "SELECT COUNT(*) FROM stories" 2>/dev/null || echo "0")
    AO3_DL=$(sqlite3 "/Volumes/David External/ao3_roleplay/stories.db" "SELECT COUNT(*) FROM stories WHERE downloaded=1" 2>/dev/null || echo "0")
    echo "  AO3 Roleplay: $AO3_DL / $AO3_IDX downloaded"
fi

# Dark Psych
if [ -f "/Volumes/David External/dark_psych_archive/content.db" ]; then
    DP_IDX=$(sqlite3 "/Volumes/David External/dark_psych_archive/content.db" "SELECT COUNT(*) FROM content" 2>/dev/null || echo "0")
    DP_DL=$(sqlite3 "/Volumes/David External/dark_psych_archive/content.db" "SELECT COUNT(*) FROM content WHERE downloaded=1" 2>/dev/null || echo "0")
    echo "  Dark Psych:   $DP_DL / $DP_IDX downloaded"
fi

# VMag
if [ -f "/Volumes/#1/vmag_archive/articles.db" ]; then
    VMAG_IDX=$(sqlite3 "/Volumes/#1/vmag_archive/articles.db" "SELECT COUNT(*) FROM articles" 2>/dev/null || echo "0")
    VMAG_DL=$(sqlite3 "/Volumes/#1/vmag_archive/articles.db" "SELECT COUNT(*) FROM articles WHERE downloaded=1" 2>/dev/null || echo "0")
    echo "  V Magazine:   $VMAG_DL / $VMAG_IDX downloaded"
fi

# WMag
if [ -f "/Volumes/#1/wmag_archive/articles.db" ]; then
    WMAG_IDX=$(sqlite3 "/Volumes/#1/wmag_archive/articles.db" "SELECT COUNT(*) FROM articles" 2>/dev/null || echo "0")
    WMAG_DL=$(sqlite3 "/Volumes/#1/wmag_archive/articles.db" "SELECT COUNT(*) FROM articles WHERE downloaded=1" 2>/dev/null || echo "0")
    echo "  W Magazine:   $WMAG_DL / $WMAG_IDX downloaded"
fi

# WWD
if [ -f "/Volumes/#1/wwd_archive/articles.db" ]; then
    WWD_IDX=$(sqlite3 "/Volumes/#1/wwd_archive/articles.db" "SELECT COUNT(*) FROM articles" 2>/dev/null || echo "0")
    WWD_DL=$(sqlite3 "/Volumes/#1/wwd_archive/articles.db" "SELECT COUNT(*) FROM articles WHERE downloaded=1" 2>/dev/null || echo "0")
    echo "  WWD:          $WWD_DL / $WWD_IDX downloaded"
fi

echo ""
echo "📜 RECENT LOG ACTIVITY:"
echo "  Nifty:    $(tail -1 '/Volumes/David External/nifty_archive/logs/scraper.log' 2>/dev/null | head -c 80)..."
echo "  AO3:      $(tail -1 '/Volumes/David External/ao3_roleplay/logs/scraper.log' 2>/dev/null | head -c 80)..."
echo "  DarkPsy:  $(tail -1 '/Volumes/David External/dark_psych_archive/logs/scraper.log' 2>/dev/null | head -c 80)..."
echo ""
