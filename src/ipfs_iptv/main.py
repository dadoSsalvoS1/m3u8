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
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("ipfs_iptv.log")
        ]
    )

def main():
    parser = argparse.ArgumentParser(description="IPFS IPTV: Upload media and generate M3U8 playlists.")
    parser.add_argument("--dir", "-d", required=True, help="Directory containing media files to upload.")
    parser.add_argument("--output", "-o", default="playlist.m3u8", help="Output path for the M3U8 playlist.")
    parser.add_argument("--api", help="IPFS API URL (default: http://127.0.0.1:5001/api/v0)")
    parser.add_argument("--gateway", help="IPFS Gateway URL (default: http://127.0.0.1:8080/ipfs/)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()

    # Configuration
    config = Config()
    if args.api:
        config.ipfs_api_url = args.api
    if args.gateway:
        config.ipfs_gateway_url = args.gateway
    if args.verbose:
        config.log_level = "DEBUG"

    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting IPFS IPTV Script...")

    # Initialize components
    client = IPFSClient(config)
    scanner = MediaScanner(config)
    generator = PlaylistGenerator(config)

    # Check connection
    if not client.check_connection():
        logger.critical("Could not connect to IPFS. Please ensure IPFS Desktop is running.")
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
            pbar.set_postfix(file=filename)

            try:
                # Upload
                # Note: The client logs info, which might interfere with tqdm.
                # Ideally we'd redirect logs or configure tqdm logging, but for now simple standard logging is fine.
                cid = client.add_file(filepath)

                # Create item entry
                # We use the filename without extension as the title for the playlist
                title = os.path.splitext(filename)[0]
                media_items.append({
                    'name': title,
                    'cid': cid
                })

            except IPFSUploadError as e:
                logger.error(f"Failed to upload {filename}: {e}")
                # We continue to the next file instead of crashing entirely
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
    else:
        logger.warning("No items were successfully processed. Playlist not created.")

if __name__ == "__main__":
    main()
