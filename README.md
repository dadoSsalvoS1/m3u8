# IPFS IPTV Generator

This is an advanced Python script designed to integrate with IPFS Desktop (specifically on Windows, but cross-platform compatible) to create an IPTV solution. It uploads your local media files to your IPFS node and generates an M3U8 playlist with direct playback links via your local IPFS Gateway.

## Features

*   **Automated Uploads**: Recursively scans directories for media files (`.mp4`, `.mkv`, `.avi`, etc.) and uploads them to your IPFS node.
*   **IPFS Pinning**: Automatically pins uploaded content to ensure local availability.
*   **Playlist Generation**: Creates a standard `.m3u8` playlist file compatible with IPTV players (VLC, etc.).
*   **Robust Architecture**: Built with modular Python code, type hinting, and error handling suitable for corporate environments.
*   **Progress Tracking**: Includes progress bars for file processing.

## Prerequisites

1.  **Python 3.8+**: Ensure Python is installed and added to your PATH.
2.  **IPFS Desktop**: You must have IPFS Desktop installed and running.
    *   Download from: [https://github.com/ipfs/ipfs-desktop/releases](https://github.com/ipfs/ipfs-desktop/releases)
    *   Ensure the IPFS daemon is running (default API port: 5001, Gateway port: 8080).

## Installation

1.  Clone this repository or download the source code.
2.  Open a terminal/command prompt in the project root.
3.  Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script using the provided `run.py` helper script.

### Basic Usage

Upload files from a directory and generate a playlist:

```bash
python run.py --dir "C:\Path\To\My\Videos"
```

This will create `playlist.m3u8` in the current directory.

### Advanced Usage

Specify output filename and custom IPFS settings:

```bash
python run.py --dir "C:\Videos" --output "my_movies.m3u8" --api "http://127.0.0.1:5001/api/v0" --gateway "http://127.0.0.1:8080/ipfs/"
```

### Arguments

*   `--dir`, `-d`: **Required**. The directory containing your media files.
*   `--output`, `-o`: The output path for the generated playlist (default: `playlist.m3u8`).
*   `--api`: The IPFS API URL (default: `http://127.0.0.1:5001/api/v0`).
*   `--gateway`: The IPFS Gateway URL to use in the playlist (default: `http://127.0.0.1:8080/ipfs/`).
*   `--verbose`, `-v`: Enable debug logging.

## Playback

Open the generated `.m3u8` file in any media player that supports HLS/M3U playlists, such as **VLC Media Player**.

**Note:** If you want the links to be publicly accessible, you must ensure your IPFS node is online and peering, or replace the gateway URL with a public gateway (e.g., `https://ipfs.io/ipfs/`) using the `--gateway` argument. However, content propagation to public gateways may take time.

## Project Structure

*   `src/ipfs_iptv/`: Core package source code.
    *   `config.py`: Configuration settings.
    *   `ipfs_client.py`: IPFS API interaction logic.
    *   `media_scanner.py`: File system scanning logic.
    *   `playlist_generator.py`: M3U8 generation logic.
    *   `main.py`: Main application controller.
*   `run.py`: Entry point script.
*   `requirements.txt`: Python dependencies.
