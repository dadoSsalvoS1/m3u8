import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import Config, configure_logging
from app.exceptions import CloudflareBlocked
from .base import BaseScraper

logger = configure_logging()


class ApacheTorrentScraper(BaseScraper):
    name = "ApacheTorrent"
    BASE_URL = "https://apachetorrent.com"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            # https://apachetorrent.com/?s=QUERY
            search_url = f"{self.BASE_URL}/?s={query}"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Check for results
            try:
                # Based on debug: results are in .capaname
                await page.wait_for_selector(".capaname", timeout=30000)
            except Exception:
                content = await page.content()
                if "Nada encontrado" in content or "Not Found" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content or "Attention Required" in content:
                    logger.warning(f"[{self.name}] Cloudflare challenge detected.")
                    raise CloudflareBlocked(f"[{self.name}] Blocked by Cloudflare.")
                else:
                    logger.warning(f"[{self.name}] Results container not found.")
                return []

            # Extract detail links
            # Structure: .capaname > a (href)

            links = await page.locator(".capaname > a").all()

            detail_urls = []
            for link in links[:Config.MAX_DETAIL_PAGES]:
                href = await link.get_attribute("href")
                if href and self.BASE_URL in href:
                    if href not in detail_urls:
                        detail_urls.append(href)

            logger.info(f"[{self.name}] Found {len(detail_urls)} torrents. Extracting details...")

            for url in detail_urls:
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                    magnets = await page.locator('a[href^="magnet:"]').all()

                    if not magnets:
                        continue

                    title = await page.title()
                    title = title.replace("Download", "").replace("Torrent", "").replace("- Apache Torrent", "").strip()

                    info_text = ""
                    # Try generic content grab
                    content_el = page.locator(".entry-content, .content, article, #content")
                    if await content_el.count():
                        info_text = (await content_el.first.inner_text())[:500]

                    for m in magnets:
                        magnet_href = await m.get_attribute("href")

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
