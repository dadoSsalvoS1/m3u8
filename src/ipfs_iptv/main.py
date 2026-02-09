import argparse
import logging
import sys
import os
from tqdm import tqdm
from .config import Config
from .ipfs_client import IPFSClient, IPFSConnectionError, IPFSUploadError
from .media_scanner import MediaScanner
from .playlist_generator import PlaylistGenerator

def setup_logging(level_name: str):
    # Fix for Windows console encoding issues (cp1252 vs utf-8)
    if sys.platform == 'win32':
        # Reconfigure stdout/stderr to use utf-8 if possible (Python 3.7+)
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stderr.reconfigure(encoding='utf-8')
            except Exception as e:
                # If reconfigure fails, we log it but proceed, hoping for the best
                print(f"Warning: Failed to set console encoding to utf-8: {e}", file=sys.stderr)

    level = getattr(logging, level_name.upper(), logging.INFO)

    # Configure handlers
    # Use utf-8 for file handler to support all characters
    file_handler = logging.FileHandler("ipfs_iptv.log", encoding='utf-8')

    # Use sys.stdout for stream handler (which we tried to set to utf-8)
    stream_handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            stream_handler,
            file_handler
        ]
    )

def main():
    parser = argparse.ArgumentParser(description="IPFS IPTV: Upload media and generate advanced M3U8 playlists.")
    parser.add_argument("--dir", "-d", required=True, help="Directory containing media files to upload.")
    parser.add_argument("--output", "-o", default="playlist.m3u8", help="Output path for the M3U8 playlist.")
    parser.add_argument("--api", help="IPFS API URL (default: http://127.0.0.1:5001/api/v0)")
    parser.add_argument("--gateway", help="IPFS Public Gateway URL (default: https://ipfs.io/ipfs/)")
    parser.add_argument("--name", help="Playlist Name (default: IPFS Public TV)")
    parser.add_argument("--epg", help="URL for XMLTV EPG data")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()

    # Configuration
    config = Config()
    if args.api:
        config.ipfs_api_url = args.api
    if args.gateway:
        config.ipfs_gateway_url = args.gateway
    if args.name:
        config.playlist_name = args.name
    if args.epg:
        config.tvg_url = args.epg
    if args.verbose:
        config.log_level = "DEBUG"

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Advanced IPFS IPTV Script...")
    logger.info(f"Using Gateway: {config.ipfs_gateway_url}")

    # Initialize components
    client = IPFSClient(config)
    scanner = MediaScanner(config)
    generator = PlaylistGenerator(config)

    # Check connection
    if not client.check_connection():
        logger.critical("Could not connect to IPFS API. Please ensure IPFS Desktop is running.")
        sys.exit(1)

    # Scan for files
    logger.info(f"Scanning directory: {args.dir}")
    files = scanner.scan_directory(args.dir)

    if not files:
        logger.warning("No media files found to process.")
        sys.exit(0)

    # Process files
    media_items = []

    # Progress bar for the list of files
    with tqdm(total=len(files), desc="Processing Files", unit="file") as pbar:
        for filepath in files:
            filename = os.path.basename(filepath)
            pbar.set_postfix(file=filename[:20]) # Limit filename display length

            try:
                # Upload
                cid = client.add_file(filepath)

                # Metadata extraction
                group = scanner.get_group_from_path(filepath, args.dir)
                title = os.path.splitext(filename)[0]

                # Determine file size (optional, could be added to metadata)
                size_str = scanner.get_file_size(filepath)

                media_items.append({
                    'name': title,
                    'cid': cid,
                    'group': group,
                    'tvg_name': title, # Placeholder
                    'tvg_id': '', # Placeholder
                    'tvg_logo': '', # Placeholder
                    'duration': -1
                })

                logger.info(f"Added {title} (Group: {group}, Size: {size_str}) -> CID: {cid}")

            except IPFSUploadError as e:
                logger.error(f"Failed to upload {filename}: {e}")
            except KeyboardInterrupt:
                logger.info("Process interrupted by user.")
                sys.exit(1)
            finally:
                pbar.update(1)

    # Generate Playlist
    if media_items:
        generator.generate_m3u8(media_items, args.output)
        print(f"\nSuccess! Playlist created at: {os.path.abspath(args.output)}")
        print(f"Total items: {len(media_items)}")
        print(f"Public Link Example: {config.ipfs_gateway_url}{media_items[0]['cid']}")
    else:
        logger.warning("No items were successfully processed. Playlist not created.")

if __name__ == "__main__":
    main()
