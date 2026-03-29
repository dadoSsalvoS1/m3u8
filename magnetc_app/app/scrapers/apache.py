import asyncio
import random
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import Config, configure_logging
from app.exceptions import CloudflareBlocked
from .base import BaseScraper

logger = configure_logging()


class ApacheTorrentScraper(BaseScraper):
    name = "ApacheTorrent"
    BASE_URL = "https://apachetorrent.com"

    async def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Sleeps for a random amount of time to simulate human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"[{self.name}] Sleeping for {delay:.2f}s...")
        await asyncio.sleep(delay)

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        # Use a new page for isolation and potentially new UA if context allowed it (but we share context)
        # We can try to set extra headers if needed
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            # Meticulous operation: Randomize search URL if possible, or just be careful
            search_url = f"{self.BASE_URL}/?s={query}"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            await self._random_delay(0.5, 1.5)

            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Check for Cloudflare / Blocks first
            content = await page.content()
            if "Just a moment..." in content or "Attention Required" in content:
                logger.warning(f"[{self.name}] Cloudflare challenge detected immediately.")
                raise CloudflareBlocked(f"[{self.name}] Blocked by Cloudflare.")

            # Meticulous selector check
            # We look for .capaname first, but fallback to article/post if layout changes
            found_selector = None
            selectors_to_try = [".capaname", "article", ".post-summary", ".entry"]

            for sel in selectors_to_try:
                try:
                    if await page.locator(sel).count() > 0:
                        found_selector = sel
                        logger.info(f"[{self.name}] Found results using selector: {sel}")
                        break
                except Exception:
                    pass

            if not found_selector:
                if "Nada encontrado" in content or "Not Found" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                    return []
                else:
                    logger.warning(f"[{self.name}] No standard result containers found. HTML length: {len(content)}")
                    # Maybe log a snippet for debugging?
                    # logger.debug(f"HTML Snippet: {content[:500]}")
                    return []

            # Extract detail links
            links = []
            if found_selector == ".capaname":
                links = await page.locator(".capaname > a").all()
            else:
                # Generic fallback extraction
                # Find all links inside the container that point to the domain
                container_links = await page.locator(f"{found_selector} a").all()
                for l in container_links:
                    href = await l.get_attribute("href")
                    if href and self.BASE_URL in href and "/page/" not in href and "/category/" not in href:
                        links.append(l)

            # Deduplicate URLs
            detail_urls = []
            for link in links:
                href = await link.get_attribute("href")
                if href and href not in detail_urls:
                    detail_urls.append(href)

            # Limit
            detail_urls = detail_urls[:Config.MAX_DETAIL_PAGES]
            logger.info(f"[{self.name}] Found {len(detail_urls)} potential torrents. Extracting details...")

            for url in detail_urls:
                try:
                    await self._random_delay(1.0, 2.5) # Delay between pages
                    await page.goto(url, timeout=45000, wait_until="domcontentloaded")

                    # Extract Magnet
                    magnets = await page.locator('a[href^="magnet:"]').all()

                    if not magnets:
                        logger.debug(f"[{self.name}] No magnet found on {url}")
                        continue

                    title = await page.title()
                    title = title.replace("Download", "").replace("Torrent", "").replace("- Apache Torrent", "").strip()

                    info_text = ""
                    # Robust content grab
                    content_locators = [".entry-content", "article", "#content", ".post-content"]
                    for loc in content_locators:
                        if await page.locator(loc).count() > 0:
                            info_text = (await page.locator(loc).first.inner_text())[:800]
                            break

                    for m in magnets:
                        magnet_href = await m.get_attribute("href")
                        if not magnet_href:
                            continue

                        qualities = [k for k in Config.QUALITY_KEYWORDS if k.lower() in (title + info_text).lower()]

                        results.append({
                            "title": title,
                            "url": url,
                            "qualities": qualities,
                            "info_text": info_text,
                            "magnet": magnet_href,
                            "source": self.name
                        })

                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to extract details from {url}: {e}")

        except CloudflareBlocked:
            raise
        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        return results
