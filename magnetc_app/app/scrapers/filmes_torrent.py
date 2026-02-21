import re
import asyncio
from typing import Any, Dict, List

from playwright.async_api import BrowserContext, Page

from app.config import Config, configure_logging
from .base import BaseScraper

logger = configure_logging()


class FilmesTorrentScraper(BaseScraper):
    name = "FilmesTorrent"
    BASE_URL = "https://filmestorrent.top/"

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        try:
            logger.info(f"[{self.name}] Navigating to: {self.BASE_URL}")
            # Timeout handled by playwright, defaulting to 30s usually, but config has 60000
            try:
                await page.goto(self.BASE_URL, timeout=60000)
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load base URL: {e}")
                return []

            # Search input
            try:
                search_input = page.locator('input[name="s"].search')
                await search_input.wait_for(timeout=10000)
                await search_input.fill(query)
                await search_input.press("Enter")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to submit search: {e}")
                return []

            # Wait for results
            try:
                await page.wait_for_selector("p.search-msg", timeout=60000)
                search_msg = await page.locator("p.search-msg").inner_text()
                if "Resultado da pesquisa para:" not in search_msg:
                    logger.warning(f"[{self.name}] No results found or search failed for '{query}'")
                    return []
            except Exception as e:
                logger.warning(f"[{self.name}] Search results page didn't load properly: {e}")
                return []

            # Extract detail pages
            external_urls = await self._extract_external_urls(page)
            external_urls = external_urls[: Config.MAX_DETAIL_PAGES]

            logger.info(f"[{self.name}] Found {len(external_urls)} detail pages. processing...")

            # Visit each detail page
            for url in external_urls:
                page_results = await self._extract_magnets(page, url)
                results.extend(page_results)

        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        # Deduplicate
        unique_results = []
        seen = set()
        for r in results:
            if r['magnet'] and r['magnet'] not in seen:
                unique_results.append(r)
                seen.add(r['magnet'])

        return unique_results

    async def _extract_external_urls(self, page: Page) -> List[str]:
        detail_buttons = await page.locator("button").all()
        external_urls: set[str] = set()

        for btn in detail_buttons:
            onclick_text = await btn.get_attribute("onclick")
            if not onclick_text:
                continue

            match = re.search(r"window\.open\('([^']+)'", onclick_text)
            if not match:
                match = re.search(r"location\.href\s*=\s*'([^']+)'", onclick_text)

            if match:
                external_urls.add(match.group(1))

        return list(external_urls)

    async def _extract_magnets(self, page: Page, url: str) -> List[Dict[str, Any]]:
        results: list[dict[str, Any]] = []
        try:
            await page.goto(url, timeout=30000)
            await asyncio.sleep(0.5)

            all_buttons = await page.locator("button").all()
            found_magnets: list[dict[str, Any]] = []

            # Helper to check quality keywords
            def get_qualities(text: str) -> List[str]:
                return [k for k in Config.QUALITY_KEYWORDS if k.lower() in text.lower()]

            page_content = (await page.content())[:5000] # Limit content for search

            for b in all_buttons:
                magnet = await b.get_attribute("data-magnet")
                b_text = (await b.inner_text() or "").strip()

                if not magnet:
                    magurl = await b.get_attribute("data-url")
                    if magurl and magurl.startswith("magnet:"):
                        magnet = magurl

                if not magnet:
                    onclick = await b.get_attribute("onclick")
                    if onclick and "magnet:" in onclick:
                        found = re.search(r"(magnet:\?xt=[^'\" ]+)", onclick)
                        if found:
                            magnet = found.group(1)

                if not magnet or not magnet.startswith("magnet:"):
                    continue

                # Get context info
                info_text = ""
                info_divs = page.locator("div.download-info")
                if await info_divs.count() > 0:
                    info_text = await info_divs.first.inner_text()
                else:
                    info_text = page_content[:1000] # fallback

                title = await page.title()
                clean_title = title.replace(" - Filmes Torrent", "").strip()

                qualities = get_qualities(info_text + " " + b_text)

                found_magnets.append({
                    "title": clean_title,
                    "url": url,
                    "qualities": qualities,
                    "info_text": info_text[:200], # truncated
                    "magnet": magnet,
                    "source": self.name
                })

            if found_magnets:
                results.extend(found_magnets)

        except Exception as e:
            logger.warning(f"[{self.name}] Failed to extract from {url}: {e}")

        return results
