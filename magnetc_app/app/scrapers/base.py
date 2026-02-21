from abc import ABC, abstractmethod
from typing import Any, Dict, List
from playwright.async_api import BrowserContext
from app.exceptions import CloudflareBlocked

class BaseScraper(ABC):
    """
    Abstract base class for all torrent scrapers.
    """
    name: str = "Base"

    @abstractmethod
    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        """
        Search for a query using the provided BrowserContext.
        Returns a list of dictionaries with at least:
        - title
        - magnet
        - url (source url)
        - qualities (list of strings)
        - source (name of the scraper)

        May raise CloudflareBlocked if detection occurs.
        """
        pass
