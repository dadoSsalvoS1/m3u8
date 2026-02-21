import asyncio
import logging
from typing import List, Dict, Any

from playwright.async_api import BrowserContext

from app.database import db
from app.scrapers.generic import GenericScraper
from app.config import Config

logger = logging.getLogger("magnet_search_app")

class WebDiscovery:
    """
    Service to discover new torrent sites via search engines and scrape them.
    """

    SEARCH_ENGINE_URL = "https://duckduckgo.com/"

    async def discover_and_scrape(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        """
        1. Search for "{query} torrent magnet"
        2. Identify new domains
        3. Try GenericScraper on them
        4. Save successful domains to DB
        5. Return results
        """
        logger.info(f"[Discovery] Starting deep web scan for: {query}")

        page = await context.new_page()
        new_results = []

        try:
            # 1. Search
            await page.goto(self.SEARCH_ENGINE_URL, timeout=30000, wait_until="domcontentloaded")

            # DDG selectors
            input_sel = "input[name='q']"
            await page.wait_for_selector(input_sel)
            await page.fill(input_sel, f"{query} torrent magnet download")
            await page.press(input_sel, "Enter")

            # Wait for results
            await page.wait_for_selector(".react-results--main", timeout=10000)

            # Extract links
            links = await page.locator("article h2 a").all()
            candidate_urls = []
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    candidate_urls.append(href)

            logger.info(f"[Discovery] Found {len(candidate_urls)} candidate URLs.")

            # 2. Filter known domains
            known_sites = db.get_active_sites()
            known_domains = [s['domain'] for s in known_sites]

            candidates = []
            from urllib.parse import urlparse

            for url in candidate_urls:
                parsed = urlparse(url)
                domain = f"{parsed.scheme}://{parsed.netloc}"

                # Skip known
                if any(d in domain for d in known_domains):
                    continue
                # Skip search engines or generic sites (simplified blacklist)
                if "google" in domain or "duckduckgo" in domain or "youtube" in domain:
                    continue

                if domain not in candidates:
                    candidates.append(domain)

            logger.info(f"[Discovery] {len(candidates)} new candidate domains to check.")

            # 3. Try Generic Scraper
            for domain in candidates[:3]: # Limit to top 3 new sites to avoid long waits
                try:
                    logger.info(f"[Discovery] Probing {domain}...")
                    scraper = GenericScraper(domain)
                    # We use the original query to search on this new site
                    site_results = await scraper.search(context, query)

                    if site_results:
                        logger.info(f"[Discovery] Success! Found {len(site_results)} items on {domain}.")
                        # 4. Save to DB
                        db.add_discovered_site(domain)
                        new_results.extend(site_results)
                    else:
                        logger.info(f"[Discovery] No results on {domain}.")

                except Exception as e:
                    logger.warning(f"[Discovery] Failed to probe {domain}: {e}")

        except Exception as e:
            logger.error(f"[Discovery] Error: {e}")
        finally:
            await page.close()

        return new_results

discovery = WebDiscovery()
