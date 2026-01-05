#!/usr/bin/env python3
"""
Recover corrupted files from source drive (different editions)
and create list of files needing manual replacement
"""

import os
import shutil
from pathlib import Path

# Files we can recover from source (different editions but same tracks)
RECOVERABLE = {
    # AIR - Moon Safari tracks (FLAC corrupted -> ALAC from source)
    "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 1998 - Moon Safari - (Europe - Source – 7243 8 44978 2 8) - [FLAC]/01 - La Femme D'Argent.flac":
        "/Volumes/David External/_Music Lossless/AIR/Albums/[AIR] - 2008 - Moon Safari - (10th Anniversary Special Edition) - (EU - Virgin ‎– CDVIRX225) - [ALAC]/CD 1/01  -  AIR    -    La Femme D'argent      .m4a",

    "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 1998 - Moon Safari - (Europe - Source – 7243 8 44978 2 8) - [FLAC]/07 - You Make It Easy.flac":
        "/Volumes/David External/_Music Lossless/AIR/Albums/[AIR] - 2008 - Moon Safari - (10th Anniversary Special Edition) - (EU - Virgin ‎– CDVIRX225) - [ALAC]/CD 1/07  -  AIR    -    You Make It Easy      .m4a",

    # AIR - 10,000 Hz Legend tracks
    "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (US - Astralwerks – ASW 10332-2) - [FLAC]/03 - Radio #1.flac":
        "/Volumes/David External/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (EU - Virgin - 724381033227) - [ALAC]/03  -  AIR    -    Radio #1      .m4a",

    "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (US - Astralwerks – ASW 10332-2) - [FLAC]/04 - The Vagabond.flac":
        "/Volumes/David External/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (EU - Virgin - 724381033227) - [ALAC]/04  -  AIR    -    The Vagabond      .m4a",

    "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (US - Astralwerks – ASW 10332-2) - [FLAC]/05 - Radian.flac":
        "/Volumes/David External/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (EU - Virgin - 724381033227) - [ALAC]/05  -  AIR    -    Radian      .m4a",

    "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (US - Astralwerks – ASW 10332-2) - [FLAC]/07 - Sex Born Poison.flac":
        "/Volumes/David External/_Music Lossless/AIR/Albums/[AIR] - 2001 - 10,000 Hz Legend - (EU - Virgin - 724381033227) - [ALAC]/07  -  AIR    -    Sex Born Poison      .m4a",
}

# Files that need manual download (no source available)
NEEDS_DOWNLOAD = [
    # AIR - Casanova 70 (single, not on source)
    {
        "artist": "AIR",
        "album": "Casanova 70 (1996)",
        "track": "03 - Casanova 70 (The Secret Of Cool)",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/AIR/Albums/[AIR] - 1996 - Casanova 70 - (France - Source Lab – 7243 8 93657 2 6) - [FLAC]/03 - Casanova 70 (The Secret Of Cool).flac"
    },
    # Afroman
    {
        "artist": "Afroman",
        "album": "Happy To Be Alive (2016)",
        "track": "11 - Palmdale (Palmdale Session)",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Afroman/Albums/[Afroman] - 2016 - Happy To Be Alive - (US - X-Ray Records – 0304) - [FLAC]/11 - Palmdale (Palmdale Session).flac"
    },
    # Alice Glass - entire album
    {
        "artist": "Alice Glass",
        "album": "Alice Glass (2017)",
        "track": "01 - Without Love",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Alice Glass/Albums/[Alice Glass] - 2017 - Alice Glass - (US - Loma Vista – LVR00245) - [FLAC]/01 - Without Love.flac"
    },
    {
        "artist": "Alice Glass",
        "album": "Alice Glass (2017)",
        "track": "02 - Forgiveness",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Alice Glass/Albums/[Alice Glass] - 2017 - Alice Glass - (US - Loma Vista – LVR00245) - [FLAC]/02 - Forgiveness.flac"
    },
    {
        "artist": "Alice Glass",
        "album": "Alice Glass (2017)",
        "track": "03 - Natural Selection",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Alice Glass/Albums/[Alice Glass] - 2017 - Alice Glass - (US - Loma Vista – LVR00245) - [FLAC]/03 - Natural Selection.flac"
    },
    {
        "artist": "Alice Glass",
        "album": "Alice Glass (2017)",
        "track": "04 - White Lies",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Alice Glass/Albums/[Alice Glass] - 2017 - Alice Glass - (US - Loma Vista – LVR00245) - [FLAC]/04 - White Lies.flac"
    },
    {
        "artist": "Alice Glass",
        "album": "Alice Glass (2017)",
        "track": "05 - Blood Oath",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Alice Glass/Albums/[Alice Glass] - 2017 - Alice Glass - (US - Loma Vista – LVR00245) - [FLAC]/05 - Blood Oath.flac"
    },
    {
        "artist": "Alice Glass",
        "album": "Alice Glass (2017)",
        "track": "06 - The Altar",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Alice Glass/Albums/[Alice Glass] - 2017 - Alice Glass - (US - Loma Vista – LVR00245) - [FLAC]/06 - The Altar.flac"
    },
    # Amtrac
    {
        "artist": "Amtrac",
        "album": "Lost In Motion Remixes (2016)",
        "track": "03 - Long Nights (Curses Remix)",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Amtrac/Albums/[Amtrac] - 2016 - Lost In Motion Remixes - (US - Super Music Group – SMG006) - [FLAC]/03 - Long Nights (Curses Remix).flac"
    },
    # Annie
    {
        "artist": "Annie",
        "album": "Anniemal (2005)",
        "track": "02 - Chewing Gum",
        "format": "ALAC",
        "path": "/Volumes/Music/_Music Lossless/Annie/Albums/[Annie] - 2005 - Anniemal - (US - Big Beat – 62304-2) - [ALAC]/02 - Chewing Gum.m4a"
    },
    # Beyonce
    {
        "artist": "Beyonce",
        "album": "I Am... Tour Instrumentals (2011)",
        "track": "16 - Listen",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Beyoncé/Albums/[Beyoncé] - 2011 - I Am... Tour Instrumentals - [FLAC]/16 - Listen.flac"
    },
    # Siriusmo - entire album section
    {
        "artist": "Siriusmo",
        "album": "Comic (2017)",
        "track": "09 - Geilomant",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Siriusmo/Albums/[Siriusmo] - 2017 - Comic - (Germany - Monkeytown Records – Monkeytown076CD) - [FLAC]/09 - Geilomant.flac"
    },
    {
        "artist": "Siriusmo",
        "album": "Comic (2017)",
        "track": "10 - Bleat",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Siriusmo/Albums/[Siriusmo] - 2017 - Comic - (Germany - Monkeytown Records – Monkeytown076CD) - [FLAC]/10 - Bleat.flac"
    },
    {
        "artist": "Siriusmo",
        "album": "Comic (2017)",
        "track": "11 - Wixn",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Siriusmo/Albums/[Siriusmo] - 2017 - Comic - (Germany - Monkeytown Records – Monkeytown076CD) - [FLAC]/11 - Wixn.flac"
    },
    {
        "artist": "Siriusmo",
        "album": "Comic (2017)",
        "track": "12 - Isegrim",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Siriusmo/Albums/[Siriusmo] - 2017 - Comic - (Germany - Monkeytown Records – Monkeytown076CD) - [FLAC]/12 - Isegrim.flac"
    },
    {
        "artist": "Siriusmo",
        "album": "Comic (2017)",
        "track": "13 - Stock Und Stein",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Siriusmo/Albums/[Siriusmo] - 2017 - Comic - (Germany - Monkeytown Records – Monkeytown076CD) - [FLAC]/13 - Stock Und Stein.flac"
    },
    {
        "artist": "Siriusmo",
        "album": "Comic (2017)",
        "track": "14 - Psychofant",
        "format": "FLAC",
        "path": "/Volumes/Music/_Music Lossless/Siriusmo/Albums/[Siriusmo] - 2017 - Comic - (Germany - Monkeytown Records – Monkeytown076CD) - [FLAC]/14 - Psychofant.flac"
    },
]

# Video files that can be re-copied from source
VIDEO_FILES = [
    "/Volumes/Music/_Music Lossless/Beyoncé/DVDs/Beyoncé - LEMONADE (The Visual Album).mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/The Circus Starring Tour Britney Spears-2009/TCSB- Final Act Live At Madison Square Garden(25-08-09)/02 -Piece Of Me  (DVD QUALITY).mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/The Circus Starring Tour Britney Spears-2009/The Circus Starring Tour-лучшее/Live From Saint Petersburg (19-07-09)/03 Radar - Saint Petersburg 19.7.2009 HD - 1.mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/Britney Spears - Apple Music Festival 2016.mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/The Circus Starring Tour Britney Spears-2009/The Circus Starring Tour-лучшее/Live in Paris - HD (05-07-09)/12 Touch Of My Hand (Live In Paris).mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/The Circus Starring Tour Britney Spears-2009/The Circus Starring Tour-лучшее/The Circus Tour-Antwerp-Belgium HD (09-07-09)/00--HD-_OPENING_COUNTDOWN_-antwerp-belgium-HD.mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/The Circus Starring Tour Britney Spears-2009/The Circus Starring Tour-лучшее/The Circus Tour-Antwerp-Belgium HD (09-07-09)/03--HD-RADAR .mp4",
    "/Volumes/Music/_Music Lossless/Britney Spears/Videos/Live Performances/The Circus Starring Tour Britney Spears-2009/The Circus Starring Tour-лучшее/The Circus Tour-Antwerp-Belgium HD (09-07-09)/12  Breath on me in HD .mp4",
]


def recover_from_source():
    """Copy replacement tracks from source drive"""
    print("=" * 60)
    print("RECOVERING FILES FROM SOURCE DRIVE")
    print("=" * 60)

    recovered = 0
    for dest, src in RECOVERABLE.items():
        if Path(src).exists():
            dest_dir = Path(dest).parent
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Note: source is ALAC, destination expected FLAC
            # Copy as-is for now (better than nothing)
            new_dest = dest.replace('.flac', '.m4a')
            print(f"Copying: {Path(src).name}")
            print(f"  -> {new_dest}")
            shutil.copy2(src, new_dest)
            recovered += 1
        else:
            print(f"Source not found: {src}")

    print(f"\nRecovered {recovered} files from source")
    return recovered


def generate_download_list():
    """Generate list of files needing manual download"""
    print("\n" + "=" * 60)
    print("FILES NEEDING MANUAL DOWNLOAD")
    print("=" * 60)

    # Group by album
    albums = {}
    for item in NEEDS_DOWNLOAD:
        key = f"{item['artist']} - {item['album']}"
        if key not in albums:
            albums[key] = []
        albums[key].append(item['track'])

    print(f"\n{len(NEEDS_DOWNLOAD)} tracks across {len(albums)} albums:\n")

    for album, tracks in albums.items():
        print(f"{album}")
        for track in tracks:
            print(f"  - {track}")
        print()

    # Write to file
    with open(Path.home() / ".sam_needs_download.txt", 'w') as f:
        f.write("# Files needing manual download\n")
        f.write(f"# Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")
        for album, tracks in albums.items():
            f.write(f"\n{album}\n")
            for track in tracks:
                f.write(f"  - {track}\n")

    print(f"Download list saved to: ~/.sam_needs_download.txt")


def main():
    print("\nSAM Corrupted File Recovery")
    print("=" * 60)

    # Step 1: Recover what we can from source
    recover_from_source()

    # Step 2: Generate download list for manual replacement
    generate_download_list()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Recoverable from source: {len(RECOVERABLE)} files")
    print(f"Need manual download: {len(NEEDS_DOWNLOAD)} files")
    print(f"Video files (already on source): {len(VIDEO_FILES)} files")


if __name__ == '__main__':
    main()
