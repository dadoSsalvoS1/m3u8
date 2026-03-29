import asyncio
import urllib.parse
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import Config, configure_logging
from app.exceptions import CloudflareBlocked
from .base import BaseScraper

logger = configure_logging()


class BTDiggScraper(BaseScraper):
    name = "BTDigg"
    BASE_URL = "https://btdig.com"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            # Correct search URL format: https://btdig.com/search?q=QUERY
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"{self.BASE_URL}/search?q={encoded_query}"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Check for results
            # BTDigg usually has div.one_result
            try:
                await page.wait_for_selector(".one_result", timeout=30000)
            except Exception:
                content = await page.content()
                if "Not found" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content:
                    logger.warning(f"[{self.name}] Cloudflare challenge detected.")
                    raise CloudflareBlocked(f"[{self.name}] Blocked.")
                else:
                    logger.warning(f"[{self.name}] Results container not found.")
                return []

            # Extract results
            # Structure:
            # <div class="one_result">
            #   <div class="torrent_name"><a href="magnet:...">Title</a></div>
            #   <div class="torrent_magnet"><a href="magnet:...">...</a></div>
            #   <div class="torrent_size">...</div>
            # </div>

            items = await page.locator(".one_result").all()

            logger.info(f"[{self.name}] Found {len(items)} results.")

            for item in items[:Config.MAX_DETAIL_PAGES]:
                try:
                    # Magnet usually in .torrent_magnet a, or .torrent_name a (sometimes direct)
                    # Actually BTDigg puts magnet in .torrent_magnet > a
                    magnet_el = item.locator(".torrent_magnet a")
                    if await magnet_el.count() == 0:
                        # Fallback
                        magnet_el = item.locator("a[href^='magnet:']")

                    if await magnet_el.count() == 0:
                        continue

                    magnet = await magnet_el.first.get_attribute("href")

                    # Title
                    title_el = item.locator(".torrent_name a")
                    if await title_el.count():
                        title = await title_el.inner_text()
                    else:
                        title = "Unknown"

                    # Info
                    info_el = item.locator(".torrent_size")
                    info_text = await info_el.inner_text() if await info_el.count() else ""

                    # Add stats if available (files, added)
                    stats_el = item.locator(".torrent_stats")
                    if await stats_el.count():
                        info_text += " " + await stats_el.inner_text()

                    qualities = [k for k in Config.QUALITY_KEYWORDS if k.lower() in (title + info_text).lower()]

                    results.append({
                        "title": title.strip(),
                        "url": search_url, # BTDigg results are often on the search page itself
                        "qualities": qualities,
                        "info_text": info_text,
                        "magnet": magnet,
                        "source": self.name
                    })

                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to extract item: {e}")

        except CloudflareBlocked:
            raise
        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        return results
