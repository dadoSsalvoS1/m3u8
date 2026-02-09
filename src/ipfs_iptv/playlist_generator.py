import os
import logging
import urllib.parse
from typing import List, Dict
from .config import Config

logger = logging.getLogger(__name__)

class PlaylistGenerator:
    def __init__(self, config: Config):
        self.config = config

    def generate_m3u8(self, media_items: List[Dict[str, str]], output_path: str):
        """
        Generates an advanced M3U8 playlist file.

        Args:
            media_items: List of dicts, each containing 'name', 'cid', 'group', 'tvg_id', etc.
            output_path: Path to save the M3U8 file.
        """
        if not media_items:
            logger.warning("No media items to generate playlist.")
            return

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                # Header with advanced metadata
                f.write("#EXTM3U")
                if self.config.tvg_url:
                    f.write(f' x-tvg-url="{self.config.tvg_url}"')
                f.write(f'\n#PLAYLIST:{self.config.playlist_name}\n\n')

                for item in media_items:
                    name = item.get('name', 'Unknown')
                    cid = item.get('cid')

                    if not cid:
                        continue

                    # Metadata extraction
                    group = item.get('group', 'Uncategorized')
                    tvg_id = item.get('tvg_id', '')
                    tvg_logo = item.get('tvg_logo', '')
                    tvg_name = item.get('tvg_name', name)
                    duration = item.get('duration', -1)

                    # Construct URL
                    # Primary URL using the main configured gateway
                    url = f"{self.config.ipfs_gateway_url}{cid}"
                    # Ensure filename is part of URL for some players to detect extension correctly
                    # IPFS gateway allows appending /filename.ext
                    filename_ext = os.path.splitext(name)[1]
                    if filename_ext:
                         # URL encode the filename to be safe
                        safe_name = urllib.parse.quote(name)
                        url = f"{url}?filename={safe_name}"

                    # Extended M3U tag construction
                    # #EXTINF:-1 tvg-id="" tvg-name="" tvg-logo="" group-title="",Title
                    extinf = f'#EXTINF:{duration} tvg-id="{tvg_id}" tvg-name="{tvg_name}" tvg-logo="{tvg_logo}" group-title="{group}",{name}'

                    f.write(f"{extinf}\n")
                    f.write(f"{url}\n")

                    # Add fallback links as comments or separate entries if player supports it?
                    # Standard M3U8 doesn't support multiple URLs for same stream easily without variant streams.
                    # We will add them as comments for manual usage if needed.
                    for fallback in self.config.fallback_gateways:
                         f.write(f"# EXT-X-ALTERNATE: {fallback}{cid}\n")

            logger.info(f"Advanced Playlist generated successfully at {output_path}")

        except IOError as e:
            logger.error(f"Failed to write playlist to {output_path}: {e}")
