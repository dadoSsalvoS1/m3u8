import asyncio
import re
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import Config, configure_logging
from app.exceptions import CloudflareBlocked
from .base import BaseScraper
from .utils import random_delay

logger = configure_logging()


class GenericScraper(BaseScraper):
    """
    A heuristic scraper for unknown torrent sites.
    It looks for magnet links and tries to deduce the title.
    """

    def __init__(self, base_url: str, name: str = None):
        self.BASE_URL = base_url.rstrip("/")
        # If no name provided, derive from domain
        if not name:
            from urllib.parse import urlparse
            self.name = urlparse(base_url).netloc.replace("www.", "").split(".")[0].capitalize()
        else:
            self.name = name

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            # Try generic search patterns
            # Most sites use /search/QUERY or /?s=QUERY
            # We try ?s= first as it is most common for generic CMS (WordPress etc)
            search_url = f"{self.BASE_URL}/?s={query}"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            try:
                await page.goto(search_url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                # Retry with /search/ path
                try:
                    search_url = f"{self.BASE_URL}/search/{query}"
                    logger.info(f"[{self.name}] Retry navigating to: {search_url}")
                    await page.goto(search_url, timeout=45000, wait_until="domcontentloaded")
                except Exception:
                    logger.error(f"[{self.name}] Failed to load URL")
                    return []

            content = await page.content()
            if "Just a moment..." in content:
                logger.warning(f"[{self.name}] Cloudflare blocked.")
                # We might raise CloudflareBlocked here if we want to retry headed
                # For generic discovery, maybe skip or raise
                raise CloudflareBlocked(f"[{self.name}] Blocked.")

            # Identify detail links
            # Strategy: Find links that are internal and look like posts (not page/tag/category)
            # Or find links that contain the query words (simplified)

            links = await page.locator("a").all()
            detail_urls = set()

            for link in links:
                href = await link.get_attribute("href")
                if not href: continue

                if href.startswith("/"):
                    href = self.BASE_URL + href

                if self.BASE_URL in href and query.lower().split()[0] in href.lower():
                    # Very rough heuristic: if URL contains part of query
                    detail_urls.add(href)

            # Limit
            detail_urls = list(detail_urls)[:5] # Low limit for generic

            logger.info(f"[{self.name}] Found {len(detail_urls)} potential matches.")

            for url in detail_urls:
                try:
                    await random_delay(1, 2)
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                    magnets = await page.locator('a[href^="magnet:"]').all()
                    if not magnets:
                        continue

                    title = await page.title()

                    # Clean title
                    title = title.replace("Download", "").replace("Torrent", "").strip()

                    # Info text (generic)
                    info_text = ""
                    # Try to find file size pattern
                    body_text = await page.inner_text("body")
                    size_match = re.search(r"(\d+(\.\d+)?\s?(GB|MB))", body_text)
                    if size_match:
                        info_text += f"Size: {size_match.group(1)} "

                    for m in magnets:
                        magnet_href = await m.get_attribute("href")
                        if not magnet_href: continue

                        # Qualities check
                        qualities = [k for k in Config.QUALITY_KEYWORDS if k.lower() in (title + body_text).lower()]

                        results.append({
                            "title": title,
                            "url": url,
                            "qualities": qualities,
                            "info_text": info_text,
                            "magnet": magnet_href,
                            "source": self.name + " (Generic)"
                        })

                except Exception:
                    pass

        except CloudflareBlocked:
            raise
        except Exception as e:
            logger.warning(f"[{self.name}] Generic search error: {e}")
        finally:
            await page.close()

        return results
