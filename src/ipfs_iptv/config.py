from dataclasses import dataclass, field
from typing import List

@dataclass
class Config:
    """
    Configuration for the IPFS IPTV Script.
    """
    ipfs_api_url: str = "http://127.0.0.1:5001/api/v0"
    ipfs_gateway_url: str = "http://127.0.0.1:8080/ipfs/"
    media_extensions: List[str] = field(default_factory=lambda: [
        ".mp4", ".mkv", ".avi", ".ts", ".mov", ".flv", ".webm"
    ])
    log_level: str = "INFO"

    def __post_init__(self):
        # Ensure URLs end with a slash if needed, though for API it might not be strictly necessary depending on usage
        if not self.ipfs_gateway_url.endswith("/"):
            self.ipfs_gateway_url += "/"
