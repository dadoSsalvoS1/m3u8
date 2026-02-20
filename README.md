# Advanced IPFS IPTV Generator

This is an enterprise-grade Python tool designed to create a decentralized IPTV solution using IPFS (InterPlanetary File System). It automates the process of uploading local media libraries to an IPFS node and generating advanced, feature-rich M3U8 playlists compatible with modern IPTV players.

## Key Features

*   **Decentralized Public Access**: Generates playback links using public IPFS gateways (e.g., `ipfs.io`, `dweb.link`), allowing content to be accessed from anywhere without port forwarding.
*   **Smart Metadata Extraction**: automatically organizes content into "Groups" based on your directory structure (e.g., `Movies/Action` becomes Group: `Action`).
*   **Advanced M3U8 Support**:
    *   Supports `tvg-id`, `tvg-name`, `tvg-logo` tags for EPG integration.
    *   Includes `x-tvg-url` header for XMLTV guides.
    *   Adds fallback gateway links for high availability.
*   **Robust & Windows-Ready**: specific fixes for Windows console encoding (UTF-8) to handle international filenames without crashing.
*   **Automated Uploads & Pinning**: Recursively scans and pins content to your local IPFS node to ensure availability.

## Prerequisites

1.  **Python 3.8+**: Ensure Python is installed and added to your PATH.
2.  **IPFS Desktop**: You must have IPFS Desktop installed and running.
    *   Download: [https://github.com/ipfs/ipfs-desktop/releases](https://github.com/ipfs/ipfs-desktop/releases)
    *   Ensure the IPFS daemon is running (API port: 5001).

## Installation

1.  Clone this repository.
2.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Use the `run.py` helper script to execute the tool.

### Basic Public Playlist

Upload all videos from a folder and create a public playlist:

```bash
python run.py --dir "C:\Users\You\Videos\Movies"
```

### Organizing Content (Groups)

If your folder structure is:
```
C:\Videos\
  ├── Action\
  │     ├── DieHard.mp4
  ├── Comedy\
  │     ├── Superbad.mp4
```

Running:
```bash
python run.py --dir "C:\Videos"
```
Will automatically create groups `Action` and `Comedy` in your IPTV player.

### Advanced Usage (EPG & Custom Gateway)

Specify a custom playlist name, an EPG source URL, and a specific public gateway:

```bash
python run.py --dir "C:\Videos" --output "public_tv.m3u8" --name "My Global TV" --epg "http://example.com/guide.xml" --gateway "https://cloudflare-ipfs.com/ipfs/"
```

### Arguments

*   `--dir`, `-d`: **Required**. Root directory containing media files.
*   `--output`, `-o`: Output filename (default: `playlist.m3u8`).
*   `--gateway`: Public IPFS Gateway URL (default: `https://ipfs.io/ipfs/`).
*   `--name`: Name of the playlist (displayed in some players).
*   `--epg`: URL to an XMLTV EPG file.
*   `--api`: Local IPFS API URL (default: `http://127.0.0.1:5001/api/v0`).
*   `--verbose`, `-v`: Enable debug logging.

## Playback

Open the generated `.m3u8` file in players like:
*   **VLC Media Player**
*   **TiviMate** (Android TV)
*   **IPTV Smarters**

**Note:** For public links to work reliably, your IPFS node must be online and peering. Content propagation to public gateways (like `ipfs.io`) may take a few minutes initially.

## Architecture

*   `src/ipfs_iptv/`:
    *   `config.py`: Centralized configuration with fallback gateways.
    *   `ipfs_client.py`: Handles multipart uploads and pinning.
    *   `media_scanner.py`: Scans directories and extracts group metadata.
    *   `playlist_generator.py`: Constructs M3U8 with extended tags.
    *   `main.py`: CLI entry point with Windows encoding safety.
