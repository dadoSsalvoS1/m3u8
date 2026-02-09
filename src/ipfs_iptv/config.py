from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    """
    Configuration for the IPFS IPTV Script.
    """
    ipfs_api_url: str = "http://127.0.0.1:5001/api/v0"
    # Default public gateway for universal access
    ipfs_gateway_url: str = "https://ipfs.io/ipfs/"

    # Advanced: Fallback gateways for reliability
    fallback_gateways: List[str] = field(default_factory=lambda: [
        "https://dweb.link/ipfs/",
        "https://cloudflare-ipfs.com/ipfs/",
        "https://gateway.pinata.cloud/ipfs/"
    ])

    media_extensions: List[str] = field(default_factory=lambda: [
        ".mp4", ".mkv", ".avi", ".ts", ".mov", ".flv", ".webm"
    ])
    log_level: str = "INFO"

    # Metadata settings
    playlist_name: str = "IPFS Public TV"
    tvg_url: str = ""  # URL for EPG (Electronic Program Guide)

    def __post_init__(self):
        # Ensure URLs end with a slash
        if not self.ipfs_gateway_url.endswith("/"):
            self.ipfs_gateway_url += "/"

        self.fallback_gateways = [
            gw if gw.endswith("/") else gw + "/" for gw in self.fallback_gateways
        ]
