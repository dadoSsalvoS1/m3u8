import os
import logging
from typing import List, Generator
from .config import Config

logger = logging.getLogger(__name__)

class MediaScanner:
    def __init__(self, config: Config):
        self.config = config

    def scan_directory(self, path: str) -> List[str]:
        """
        Recursively finds files in the given directory that match the configured extensions.
        """
        if not os.path.exists(path):
            logger.error(f"Directory not found: {path}")
            return []

        media_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in self.config.media_extensions):
                    full_path = os.path.join(root, file)
                    media_files.append(full_path)

        logger.info(f"Found {len(media_files)} media files in {path}")
        return media_files

    @staticmethod
    def get_group_from_path(filepath: str, root_dir: str) -> str:
        """
        Extracts a group name from the directory structure relative to the root scan directory.
        e.g., C:\Videos\Movies\Action\DieHard.mp4 -> Group: "Movies/Action"
        """
        rel_path = os.path.relpath(os.path.dirname(filepath), root_dir)
        if rel_path == ".":
            return "Uncategorized"
        # Normalize slashes to forward slashes for consistency
        return rel_path.replace(os.sep, "/")

    @staticmethod
    def get_file_size(filepath: str) -> str:
        """Helper to get human-readable file size."""
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
