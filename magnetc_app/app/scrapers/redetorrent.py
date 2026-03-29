import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import Config, configure_logging
from app.exceptions import CloudflareBlocked
from .base import BaseScraper

logger = configure_logging()


class RedeTorrentScraper(BaseScraper):
    name = "RedeTorrent"
    BASE_URL = "https://redetorrent.com"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            # Based on the form in redetorrent_home.html:
            # <form method="GET" action="index.php" id='pesquisa'>
            # <input name="s">
            # So the URL is https://redetorrent.com/index.php?s=QUERY or just /?s=QUERY

            search_url = f"{self.BASE_URL}/?s={query}"
            logger.info(f"[{self.name}] Navigating to: {search_url}")

            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Check for results
            # The structure seems to be .capa_lista containing anchors to details
            try:
                await page.wait_for_selector(".capa_lista", timeout=30000)
            except Exception:
                content = await page.content()
                # Check for "Não encontrado" or similar
                if "Nada encontrado" in content or "Não encontramos" in content:
                    logger.info(f"[{self.name}] No results found for '{query}'")
                elif "Just a moment..." in content or "Attention Required" in content:
                    logger.warning(f"[{self.name}] Cloudflare challenge detected.")
                    raise CloudflareBlocked(f"[{self.name}] Blocked by Cloudflare.")
                else:
                    logger.warning(f"[{self.name}] Results container not found.")
                return []

            # Extract detail links
            links = await page.locator(".capa_lista > a:first-child").all()

            detail_urls = []
            for link in links[:Config.MAX_DETAIL_PAGES]:
                href = await link.get_attribute("href")
                if href:
                    detail_urls.append(href)

            logger.info(f"[{self.name}] Found {len(detail_urls)} torrents. Extracting details...")

            for url in detail_urls:
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                    # Magnet link extraction
                    # Usually RedeTorrent has buttons with text "Magnet Link" or icon
                    # Let's search for href^="magnet:"
                    magnets = await page.locator('a[href^="magnet:"]').all()

                    if not magnets:
                        # Sometimes they use onclick or javascript obfuscation, but usually plain magnets are there
                        # Check for "Baixar" buttons that might have magnet in href
                        pass

                    # Title
                    title = await page.title()
                    # Clean up title
                    title = title.replace("Torrent Download", "").replace("- Rede Torrent", "").strip()

                    # Info text
                    # Usually in a content div, e.g. .sinopse or similar
                    # From HTML snippet, <div class='dados_capa'> has some info, but detail page has more.
                    # Let's grab generic text from the main content area if possible.
                    # Assuming standard wordpress-like structure or similar
                    info_text = ""
                    # Try finding "Sinopse" or similar containers
                    content_div = page.locator("article") # generic guess
                    if await content_div.count():
                        info_text = (await content_div.inner_text())[:500]

                    # There might be multiple magnets (720p, 1080p, 4k)
                    # We should try to associate quality with magnet if possible
                    # Often the structure is: <strong>720p</strong> <a href="magnet...">Baixar</a>

                    for m in magnets:
                        magnet_href = await m.get_attribute("href")

                        # Try to find quality text near the button
                        # Parent element text?
                        # parent = m.locator("..")
                        # quality_text = await parent.inner_text()

                        # For now, just add them with global qualities check
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

        # Deduplicate results from same page (e.g. if we found multiple magnets for same movie,
        # we might want to keep them, but current logic allows it)
        return results
