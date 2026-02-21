import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import configure_logging
from app.exceptions import CloudflareBlocked
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
                # Wait longer for initial load in case of redirects/challenges
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Wait for table or no results, handling Cloudflare/Challenge
            try:
                # TPB uses client-side rendering with <ol id="torrents"> OR legacy table #searchResult
                # We wait for either.
                await page.wait_for_selector("#torrents, #searchResult", timeout=30000)
            except Exception:
                # Check for "No results" text if possible, or just return empty
                content = await page.content()
                if "No hits. Try adding an asterisk" in content or "No results" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content or "Attention Required" in content:
                    logger.warning(f"[{self.name}] Cloudflare challenge detected.")
                    raise CloudflareBlocked(f"[{self.name}] Blocked by Cloudflare.")
                else:
                    logger.warning(f"[{self.name}] Search results container not found.")
                return []

            # Parsing logic
            # Check which structure we have
            if await page.locator("#torrents").count() > 0:
                # New JS structure
                rows = await page.locator("#torrents li").all()
                # Skip header if it exists (class list-header)

                for row in rows:
                    class_attr = await row.get_attribute("class") or ""
                    if "list-header" in class_attr:
                        continue

                    # Magnet: .item-icons a[href^="magnet:"]
                    magnet_link = row.locator('.item-icons a[href^="magnet:"]').first
                    if await magnet_link.count() == 0:
                        continue
                    magnet = await magnet_link.get_attribute("href")

                    # Title: .item-name a or .item-title a
                    title_el = row.locator(".item-name a, .item-title a").first
                    if await title_el.count():
                        title = await title_el.inner_text()
                        url = await title_el.get_attribute("href") or ""
                        if url and not url.startswith("http"):
                            url = self.BASE_URL + url
                    else:
                        title = "Unknown Title"
                        url = search_url

                    # Info: .item-size, .item-uploaded, .item-seed, .item-leech
                    # We can aggregate them into info_text
                    size = await row.locator(".item-size").inner_text() if await row.locator(".item-size").count() else ""
                    uploaded = await row.locator(".item-uploaded").inner_text() if await row.locator(".item-uploaded").count() else ""
                    seeders = await row.locator(".item-seed").inner_text() if await row.locator(".item-seed").count() else ""

                    info_text = f"Size: {size}, Uploaded: {uploaded}, Seeds: {seeders}"

                    results.append({
                        "title": title.strip(),
                        "url": url,
                        "qualities": [],
                        "info_text": info_text,
                        "magnet": magnet,
                        "source": self.name
                    })

            elif await page.locator("#searchResult tr").count() > 0:
                # Old table structure (legacy fallback)
                rows = await page.locator("#searchResult tr").all()

                if not rows:
                    return []

                first_row_text = await rows[0].inner_text()
                start_idx = 1 if "Type" in first_row_text and "Name" in first_row_text else 0

                for i in range(start_idx, len(rows)):
                    row = rows[i]

                    # Magnet
                    magnet_link = row.locator('.item-icons a[href^="magnet:"], a[href^="magnet:"]').first
                    if await magnet_link.count() == 0:
                        continue
                    magnet = await magnet_link.get_attribute("href")

                    # Title
                    title_el = row.locator(".detName a").first
                    if await title_el.count() == 0:
                        title_el = row.locator("a.detLink").first

                    if await title_el.count():
                        title = await title_el.inner_text()
                        url = await title_el.get_attribute("href") or ""
                        if url and not url.startswith("http"):
                            url = self.BASE_URL + url
                    else:
                        title = "Unknown Title"
                        url = search_url

                    info_el = row.locator("font.detDesc")
                    info_text = await info_el.inner_text() if await info_el.count() else ""

                    results.append({
                        "title": title.strip(),
                        "url": url,
                        "qualities": [],
                        "info_text": info_text,
                        "magnet": magnet,
                        "source": self.name
                    })

        except CloudflareBlocked:
            raise
        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        logger.info(f"[{self.name}] Found {len(results)} results.")
        return results
