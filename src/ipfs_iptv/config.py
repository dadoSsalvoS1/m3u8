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
    # Format strings allow using {cid} for v0 (Qm...) or {cid_v1} for v1 base32 (bafy...)
    fallback_gateways: List[str] = field(default_factory=lambda: [
        "https://{cid_v1}.ipfs.dweb.link/",
        "https://gateway.pinata.cloud/ipfs/{cid}"
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

        # Don't enforce trailing slash for formatted gateways as they might be subdomains without paths
        # But for path-based ones (without {) it's good practice.
        # Since we use format strings now, we skip the automatic slash addition for fallbacks
        pass
