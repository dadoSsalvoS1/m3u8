import os
import logging
from typing import List, Dict
from .config import Config

logger = logging.getLogger(__name__)

class PlaylistGenerator:
    def __init__(self, config: Config):
        self.config = config

    def generate_m3u8(self, media_items: List[Dict[str, str]], output_path: str):
        """
        Generates an M3U8 playlist file from a list of media items.

        Args:
            media_items: List of dicts, each containing 'name' and 'cid'.
            output_path: Path to save the M3U8 file.
        """
        if not media_items:
            logger.warning("No media items to generate playlist.")
            return

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")

                for item in media_items:
                    name = item.get('name', 'Unknown')
                    cid = item.get('cid')

                    if not cid:
                        logger.warning(f"Skipping item {name} due to missing CID.")
                        continue

                    # Construct the URL
                    # Use the configured gateway
                    url = f"{self.config.ipfs_gateway_url}{cid}"

                    # EXTINF:duration,title
                    # Using -1 for duration as we might not know it without deep inspection
                    f.write(f"#EXTINF:-1,{name}\n")
                    f.write(f"{url}\n")

            logger.info(f"Playlist generated successfully at {output_path}")

        except IOError as e:
            logger.error(f"Failed to write playlist to {output_path}: {e}")
