import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext, Page

from app.config import Config, configure_logging
from .base import BaseScraper

logger = configure_logging()


class LeetXScraper(BaseScraper):
    name = "1337x"
    BASE_URL = "https://1337x.to"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            search_url = f"{self.BASE_URL}/search/{query}/1/"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            try:
                # Wait longer for initial load in case of redirects/challenges
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Check for results table, waiting longer for Cloudflare challenge
            try:
                # Wait up to 30s to allow Cloudflare check to clear automatically
                await page.wait_for_selector("table.table-list", timeout=30000)
            except Exception:
                content = await page.content()
                if "No results were found" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content or "Attention Required" in content:
                    logger.warning(f"[{self.name}] Cloudflare challenge detected. Retry logic or manual verification needed.")
                    # If headless=False, the user has a chance to see and solve it.
                else:
                    logger.warning(f"[{self.name}] Results table not found or blocked.")
                return []

            # Extract detail links
            links = await page.locator("table.table-list tbody tr td.name a[href^='/torrent/']").all()

            detail_urls = []
            for link in links[:Config.MAX_DETAIL_PAGES]: # Limit to avoid too many requests
                href = await link.get_attribute("href")
                if href:
                    detail_urls.append(self.BASE_URL + href)

            logger.info(f"[{self.name}] Found {len(detail_urls)} torrents. extracting details...")

            # Visit details
            for url in detail_urls:
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await asyncio.sleep(0.5)

                    magnet_link = page.locator('a[href^="magnet:"]').first
                    if await magnet_link.count() > 0:
                        magnet = await magnet_link.get_attribute("href")
                        title = await page.title()
                        title = title.replace("Download Torrent", "").replace("| 1337x", "").strip()

                        # Info text (e.g. description or metadata)
                        info_div = page.locator(".torrent-detail-info")
                        info_text = await info_div.inner_text() if await info_div.count() else ""

                        # simple quality extraction from title/info
                        qualities = [k for k in Config.QUALITY_KEYWORDS if k.lower() in (title + info_text).lower()]

                        results.append({
                            "title": title,
                            "url": url,
                            "qualities": qualities,
                            "info_text": info_text[:200],
                            "magnet": magnet,
                            "source": self.name
                        })
                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to extract details from {url}: {e}")

        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        return results
