#!/usr/bin/env python3
"""
SAM Booklet Server
Serves CD scans and injects booklet viewer into Navidrome

Run alongside Navidrome to add booklet viewing capability.
"""

from flask import Flask, jsonify, send_file, request, Response
import requests
import os
import re
from pathlib import Path
from functools import lru_cache

app = Flask(__name__)

# Configuration
NAVIDROME_URL = "http://localhost:4533"
CD_SCANS_DIR = Path("/Volumes/Music/_CD_Scans")
MUSIC_DIR = Path("/Volumes/Music/_Music Lossless")

# The JavaScript to inject
BOOKLET_VIEWER_JS = Path(__file__).parent / "navidrome_booklet_viewer.js"


@lru_cache(maxsize=100)
def find_album_scans(artist: str, album: str):
    """Find scan images for an album"""
    scans = []

    # Normalize names for matching
    def normalize(s):
        return re.sub(r'[^\w\s]', '', s.lower())

    artist_norm = normalize(artist)
    album_norm = normalize(album)

    # Search in CD_SCANS_DIR
    if CD_SCANS_DIR.exists():
        for artist_dir in CD_SCANS_DIR.iterdir():
            if not artist_dir.is_dir():
                continue
            if normalize(artist_dir.name) == artist_norm or artist_norm in normalize(artist_dir.name):
                for album_dir in artist_dir.iterdir():
                    if not album_dir.is_dir():
                        continue
                    if normalize(album_dir.name) == album_norm or album_norm in normalize(album_dir.name):
                        # Found matching album, get all images
                        for img in sorted(album_dir.glob('*')):
                            if img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                                scans.append(str(img))

    # Also check in the album folder itself for embedded scans
    if MUSIC_DIR.exists():
        for artist_dir in MUSIC_DIR.iterdir():
            if not artist_dir.is_dir():
                continue
            if normalize(artist_dir.name) == artist_norm:
                for subdir in artist_dir.rglob('*'):
                    if subdir.is_dir() and album_norm in normalize(subdir.name):
                        # Check for Scans subfolder
                        scans_folder = subdir / 'Scans'
                        if scans_folder.exists():
                            for img in sorted(scans_folder.glob('*')):
                                if img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                                    scans.append(str(img))

                        # Check for artwork folder
                        artwork_folder = subdir / 'Artwork'
                        if artwork_folder.exists():
                            for img in sorted(artwork_folder.glob('*')):
                                if img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                                    scans.append(str(img))

    return list(set(scans))  # Remove duplicates


@app.route('/api/scans/<path:album_path>')
def get_album_scans(album_path):
    """Get list of scan images for an album"""
    # Parse artist and album from path
    parts = album_path.split('/')
    artist = parts[0] if len(parts) > 0 else ''
    album = parts[-1] if len(parts) > 1 else parts[0]

    scans = find_album_scans(artist, album)

    # Convert to URLs
    scan_urls = [f"/scan/{i}" for i in range(len(scans))]

    return jsonify({
        'artist': artist,
        'album': album,
        'scans': scan_urls,
        'count': len(scans),
        'paths': scans  # For debugging
    })


@app.route('/scan/<int:index>')
def serve_scan(index):
    """Serve a scan image by index (from last query)"""
    # This is a simplified version - in production you'd want proper session handling
    album_path = request.args.get('album', '')
    parts = album_path.split('/')
    artist = parts[0] if len(parts) > 0 else ''
    album = parts[-1] if len(parts) > 1 else parts[0]

    scans = find_album_scans(artist, album)

    if 0 <= index < len(scans):
        return send_file(scans[index])
    return "Not found", 404


@app.route('/scan/file')
def serve_scan_file():
    """Serve a scan by file path"""
    path = request.args.get('path', '')
    if path and os.path.exists(path):
        return send_file(path)
    return "Not found", 404


@app.route('/booklet.js')
def serve_booklet_js():
    """Serve the booklet viewer JavaScript"""
    if BOOKLET_VIEWER_JS.exists():
        return Response(
            BOOKLET_VIEWER_JS.read_text(),
            mimetype='application/javascript'
        )
    return "Not found", 404


# Proxy all other requests to Navidrome and inject our JS
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """Proxy requests to Navidrome, injecting booklet viewer into HTML"""
    url = f"{NAVIDROME_URL}/{path}"

    # Forward the request
    resp = requests.request(
        method=request.method,
        url=url,
        headers={key: value for key, value in request.headers if key != 'Host'},
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False
    )

    # If it's HTML, inject our script
    content = resp.content
    if 'text/html' in resp.headers.get('Content-Type', ''):
        content = content.decode('utf-8')
        # Inject booklet viewer script before </body>
        inject_script = '<script src="/booklet.js"></script></body>'
        content = content.replace('</body>', inject_script)
        content = content.encode('utf-8')

    # Build response
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for name, value in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    return Response(content, resp.status_code, headers)


def main():
    print("=" * 50)
    print("SAM Booklet Server")
    print("=" * 50)
    print(f"CD Scans directory: {CD_SCANS_DIR}")
    print(f"Music directory: {MUSIC_DIR}")
    print(f"Proxying Navidrome at: {NAVIDROME_URL}")
    print()
    print("Access Navidrome with booklet viewer at:")
    print("  http://localhost:4534")
    print()
    print("The 'View Booklet' button will appear on album pages")
    print("=" * 50)

    app.run(host='0.0.0.0', port=4534, debug=False)


if __name__ == '__main__':
    main()
