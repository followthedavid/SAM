// ==UserScript==
// @name         Navidrome CD Booklet Viewer
// @namespace    SAM
// @version      1.0
// @description  Adds CD booklet/scan viewing to Navidrome
// @match        http://localhost:4533/*
// @match        https://*.navidrome.org/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    const CD_SCANS_BASE = '/music/lossless'; // Adjust to your scans location
    const SCAN_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp'];

    // Booklet viewer state
    let currentAlbum = null;
    let bookletImages = [];
    let currentPage = 0;
    let viewerOpen = false;

    // Create the booklet viewer UI
    function createBookletViewer() {
        const viewer = document.createElement('div');
        viewer.id = 'sam-booklet-viewer';
        viewer.innerHTML = `
            <style>
                #sam-booklet-viewer {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.95);
                    z-index: 10000;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }
                #sam-booklet-viewer.open {
                    display: flex;
                }
                .booklet-header {
                    position: absolute;
                    top: 20px;
                    left: 20px;
                    right: 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    color: white;
                }
                .booklet-title {
                    font-size: 18px;
                    font-weight: bold;
                }
                .booklet-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 32px;
                    cursor: pointer;
                    padding: 10px;
                }
                .booklet-close:hover {
                    color: #ff6b6b;
                }
                .booklet-container {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                    height: calc(100% - 120px);
                    margin-top: 60px;
                }
                .booklet-image {
                    max-width: 90%;
                    max-height: 90%;
                    object-fit: contain;
                    box-shadow: 0 10px 50px rgba(0,0,0,0.5);
                    border-radius: 4px;
                }
                .booklet-nav {
                    position: absolute;
                    top: 50%;
                    transform: translateY(-50%);
                    background: rgba(255,255,255,0.1);
                    border: none;
                    color: white;
                    font-size: 48px;
                    padding: 20px;
                    cursor: pointer;
                    border-radius: 8px;
                    transition: background 0.2s;
                }
                .booklet-nav:hover {
                    background: rgba(255,255,255,0.2);
                }
                .booklet-nav.prev { left: 20px; }
                .booklet-nav.next { right: 20px; }
                .booklet-nav:disabled {
                    opacity: 0.3;
                    cursor: not-allowed;
                }
                .booklet-footer {
                    position: absolute;
                    bottom: 20px;
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }
                .booklet-dots {
                    display: flex;
                    gap: 8px;
                }
                .booklet-dot {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.3);
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .booklet-dot.active {
                    background: white;
                }
                .booklet-dot:hover {
                    background: rgba(255,255,255,0.7);
                }
                .booklet-page-info {
                    color: rgba(255,255,255,0.7);
                    font-size: 14px;
                    margin-left: 20px;
                }
                .booklet-thumbnails {
                    display: flex;
                    gap: 10px;
                    margin-top: 10px;
                    overflow-x: auto;
                    max-width: 80%;
                    padding: 10px;
                }
                .booklet-thumb {
                    width: 60px;
                    height: 60px;
                    object-fit: cover;
                    cursor: pointer;
                    border: 2px solid transparent;
                    border-radius: 4px;
                    opacity: 0.6;
                    transition: all 0.2s;
                }
                .booklet-thumb:hover {
                    opacity: 1;
                }
                .booklet-thumb.active {
                    border-color: white;
                    opacity: 1;
                }
                #sam-booklet-btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 12px;
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    margin-left: 10px;
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                #sam-booklet-btn:hover {
                    transform: scale(1.05);
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                }
                #sam-booklet-btn svg {
                    width: 16px;
                    height: 16px;
                }
            </style>
            <div class="booklet-header">
                <span class="booklet-title" id="booklet-album-title">Album Booklet</span>
                <button class="booklet-close" onclick="SAMBooklet.close()">&times;</button>
            </div>
            <div class="booklet-container">
                <button class="booklet-nav prev" onclick="SAMBooklet.prev()">‹</button>
                <img class="booklet-image" id="booklet-main-image" src="" alt="Booklet page">
                <button class="booklet-nav next" onclick="SAMBooklet.next()">›</button>
            </div>
            <div class="booklet-footer">
                <div class="booklet-dots" id="booklet-dots"></div>
                <span class="booklet-page-info" id="booklet-page-info">Page 1 of 1</span>
            </div>
            <div class="booklet-thumbnails" id="booklet-thumbnails"></div>
        `;
        document.body.appendChild(viewer);

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!viewerOpen) return;
            if (e.key === 'Escape') SAMBooklet.close();
            if (e.key === 'ArrowLeft') SAMBooklet.prev();
            if (e.key === 'ArrowRight') SAMBooklet.next();
        });

        return viewer;
    }

    // SAM Booklet API
    window.SAMBooklet = {
        open: async function(albumPath, albumTitle) {
            currentAlbum = albumPath;
            bookletImages = await this.findScans(albumPath);
            currentPage = 0;

            if (bookletImages.length === 0) {
                alert('No booklet scans found for this album');
                return;
            }

            document.getElementById('booklet-album-title').textContent = albumTitle || 'Album Booklet';
            this.renderViewer();
            document.getElementById('sam-booklet-viewer').classList.add('open');
            viewerOpen = true;
        },

        close: function() {
            document.getElementById('sam-booklet-viewer').classList.remove('open');
            viewerOpen = false;
        },

        next: function() {
            if (currentPage < bookletImages.length - 1) {
                currentPage++;
                this.renderViewer();
            }
        },

        prev: function() {
            if (currentPage > 0) {
                currentPage--;
                this.renderViewer();
            }
        },

        goToPage: function(page) {
            currentPage = page;
            this.renderViewer();
        },

        renderViewer: function() {
            const img = document.getElementById('booklet-main-image');
            img.src = bookletImages[currentPage];

            // Update page info
            document.getElementById('booklet-page-info').textContent =
                `Page ${currentPage + 1} of ${bookletImages.length}`;

            // Update dots
            const dotsContainer = document.getElementById('booklet-dots');
            dotsContainer.innerHTML = bookletImages.map((_, i) =>
                `<div class="booklet-dot ${i === currentPage ? 'active' : ''}"
                     onclick="SAMBooklet.goToPage(${i})"></div>`
            ).join('');

            // Update thumbnails
            const thumbsContainer = document.getElementById('booklet-thumbnails');
            thumbsContainer.innerHTML = bookletImages.map((src, i) =>
                `<img class="booklet-thumb ${i === currentPage ? 'active' : ''}"
                      src="${src}" onclick="SAMBooklet.goToPage(${i})">`
            ).join('');

            // Update nav buttons
            document.querySelector('.booklet-nav.prev').disabled = currentPage === 0;
            document.querySelector('.booklet-nav.next').disabled = currentPage === bookletImages.length - 1;
        },

        findScans: async function(albumPath) {
            // Look for scans in common locations
            const scanPatterns = [
                'Scans/', 'scans/', 'Artwork/', 'artwork/',
                'Booklet/', 'booklet/', 'CD/', 'Images/'
            ];

            const images = [];

            // For now, return placeholder - in production, this would
            // query your CD scans folder structure
            // This needs to be connected to your actual scan storage

            try {
                // Try to fetch from CD_SCANS directory
                // This would need a backend endpoint to list files
                const response = await fetch(`/api/album/${encodeURIComponent(albumPath)}/scans`);
                if (response.ok) {
                    const data = await response.json();
                    return data.scans || [];
                }
            } catch (e) {
                console.log('SAM Booklet: Could not fetch scans', e);
            }

            return images;
        }
    };

    // Add booklet button to album pages
    function addBookletButton() {
        // Find the album info section
        const albumHeader = document.querySelector('[class*="albumHeader"]') ||
                           document.querySelector('[class*="AlbumDetails"]');

        if (albumHeader && !document.getElementById('sam-booklet-btn')) {
            const btn = document.createElement('button');
            btn.id = 'sam-booklet-btn';
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14zM7 17h10v-2H7v2zm0-4h10v-2H7v2zm0-4h10V7H7v2z"/>
                </svg>
                View Booklet
            `;
            btn.onclick = () => {
                // Get current album info from page
                const albumTitle = document.querySelector('[class*="albumTitle"]')?.textContent ||
                                  document.querySelector('h1')?.textContent || 'Album';
                const albumPath = window.location.pathname;
                SAMBooklet.open(albumPath, albumTitle);
            };

            // Insert after album title or cover
            const insertPoint = albumHeader.querySelector('h1') || albumHeader.firstChild;
            if (insertPoint) {
                insertPoint.parentNode.insertBefore(btn, insertPoint.nextSibling);
            }
        }
    }

    // Initialize
    function init() {
        createBookletViewer();

        // Watch for navigation changes (Navidrome is a SPA)
        const observer = new MutationObserver(() => {
            if (window.location.pathname.includes('/album/')) {
                setTimeout(addBookletButton, 500);
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });

        // Initial check
        if (window.location.pathname.includes('/album/')) {
            setTimeout(addBookletButton, 1000);
        }

        console.log('SAM Booklet Viewer loaded');
    }

    // Wait for page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
