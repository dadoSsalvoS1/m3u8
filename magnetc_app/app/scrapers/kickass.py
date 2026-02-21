import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import Config, configure_logging
from app.exceptions import CloudflareBlocked
from .base import BaseScraper

logger = configure_logging()


class KickassTorrentsScraper(BaseScraper):
    name = "KickassTorrents"
    BASE_URL = "https://kickasstorrents.cr"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            search_url = f"{self.BASE_URL}/search/{query}/"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Check for Cloudflare or Results
            try:
                # Wait for results: .torrentname OR tr.odd/tr.even
                await page.wait_for_selector(".torrentname, tr.odd, tr.even", timeout=30000)
            except Exception:
                content = await page.content()
                if "No files found" in content or "Nothing found" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content or "Attention Required" in content:
                    logger.warning(f"[{self.name}] Cloudflare challenge detected.")
                    raise CloudflareBlocked(f"[{self.name}] Blocked by Cloudflare.")
                else:
                    # Check manually for rows if selector failed but content loaded
                    if await page.locator("tr").count() > 5:
                         logger.info(f"[{self.name}] Table rows found despite timeout on specific class.")
                    else:
                        logger.warning(f"[{self.name}] Results container not found.")
                        return []

            # Extract results
            rows = await page.locator("tr.odd, tr.even").all()
            if not rows:
                # Fallback: look for any row with links
                rows = await page.locator("tr").all()

            detail_urls = []
            for row in rows[:Config.MAX_DETAIL_PAGES]:
                # Find the title link
                # Priority: .torrentname a, then celltext a, then any a
                link = row.locator(".torrentname a.normalgrey")
                if await link.count() == 0:
                    link = row.locator(".celltext a").first
                if await link.count() == 0:
                    # heuristic: find link that is not user/category
                    links = await row.locator("a").all()
                    for l in links:
                        href = await l.get_attribute("href")
                        if href and "user" not in href and "category" not in href and ".html" in href:
                            link = l
                            break

                if isinstance(link, list): continue # generic fallback failed or empty

                if await link.count() > 0:
                    href = await link.get_attribute("href")
                    if href:
                        detail_urls.append(self.BASE_URL + href)

            logger.info(f"[{self.name}] Found {len(detail_urls)} torrents. Extracting details...")

            for url in detail_urls:
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                    # Look for magnet link on detail page
                    # Usually <a class="kaGiantButton" href="magnet:..."> or similar
                    magnet_link = page.locator('a[href^="magnet:"]').first

                    if await magnet_link.count() > 0:
                        magnet = await magnet_link.get_attribute("href")
                        title = await page.title()
                        title = title.replace("Download", "").replace("Torrent", "").replace("- Kickass Torrents", "").strip()

                        # Info text
                        info_div = page.locator(".data")
                        info_text = ""
                        if await info_div.count():
                            info_text = await info_div.first.inner_text()

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

        except CloudflareBlocked:
            raise
        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        return results
