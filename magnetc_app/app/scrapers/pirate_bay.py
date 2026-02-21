import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import configure_logging
from .base import BaseScraper

logger = configure_logging()


class PirateBayScraper(BaseScraper):
    name = "ThePirateBay"
    # Using a common proxy or the main site if accessible.
    # TPB often changes domains.
    BASE_URL = "https://thepiratebay.org"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        # TPB search URL pattern: /search/{query}/{page}/{sort}/{category}
        # sort 99 = default/relevance? often 7=seeders.
        # category 0 = all
        search_url = f"{self.BASE_URL}/search/{query}/1/99/0"

        try:
            logger.info(f"[{self.name}] Navigating to: {search_url}")
            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Wait for table or no results
            try:
                # Expecting a table with id 'searchResult'
                await page.wait_for_selector("#searchResult", timeout=15000)
            except Exception:
                # Check for "No results" text if possible, or just return empty
                content = await page.content()
                if "No hits. Try adding an asterisk" in content or "No results" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content or "Attention Required" in content:
                    logger.warning(f"[{self.name}] Cloudflare blocked request.")
                else:
                    logger.warning(f"[{self.name}] Search results table not found.")
                return []

            # Parse rows
            rows = await page.locator("#searchResult tr").all()

            # Skip header row (usually first one)
            if not rows:
                return []

            # Helper to check if row is header
            first_row_text = await rows[0].inner_text()
            start_idx = 1 if "Type" in first_row_text and "Name" in first_row_text else 0

            for i in range(start_idx, len(rows)):
                row = rows[i]

                # Check for magnet link
                magnet_link = await row.locator('a[href^="magnet:"]').first
                if not await magnet_link.count():
                    continue

                magnet = await magnet_link.get_attribute("href")

                # Title usually in .detName > a
                title_el = row.locator(".detName a")
                if await title_el.count():
                    title = await title_el.inner_text()
                    url = await title_el.get_attribute("href") or ""
                    if url and not url.startswith("http"):
                        url = self.BASE_URL + url
                else:
                    title = "Unknown Title"
                    url = search_url

                # Info text (Size, Uploaded, etc.)
                info_el = row.locator("font.detDesc")
                info_text = await info_el.inner_text() if await info_el.count() else ""

                # Extract seeders/leechers if needed, usually in td:nth-child(...)
                # But info_text is often enough for "qualities" check or just display.

                results.append({
                    "title": title.strip(),
                    "url": url,
                    "qualities": [], # TPB doesn't explicitly tag qualities easily, we parse title/info later or rely on title
                    "info_text": info_text,
                    "magnet": magnet,
                    "source": self.name
                })

        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        logger.info(f"[{self.name}] Found {len(results)} results.")
        return results
