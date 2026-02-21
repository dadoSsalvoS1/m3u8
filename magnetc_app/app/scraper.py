import asyncio
from typing import Any, Dict, List

from playwright.async_api import async_playwright

from .config import Config, configure_logging
from .scrapers import FilmesTorrentScraper, PirateBayScraper, LeetXScraper, YTSScraper

logger = configure_logging()

# Global config for headless mode, can be set by app factory or run.py
HEADLESS_MODE = True

def set_headless_mode(headless: bool):
    global HEADLESS_MODE
    HEADLESS_MODE = headless

async def search_movie(
    query: str,
    *,
    search_url: str | None = None,
    quality_keywords: list[str] | None = None,
    max_detail_pages: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Orchestrate search across multiple torrent sites.
    """
    if not query or not query.strip():
        return []

    logger.info(f"Starting search for query: '{query}' (Headless: {HEADLESS_MODE})")

    results: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS_MODE,
            args=["--disable-blink-features=AutomationControlled"],
            # If not headless, we might want to slow down slightly or just let user see
        )
        # Create a shared context. Note: some sites might need separate contexts if cookies conflict,
        # but for simple scraping shared context is usually fine and faster.
        context = await browser.new_context(
            user_agent=Config.MAGNET_SITE_USER_AGENT,
            viewport={"width": 1280, "height": 720}, # Better viewport for headed
        )

        scrapers = [
            FilmesTorrentScraper(),
            PirateBayScraper(),
            LeetXScraper(),
            YTSScraper(),
        ]

        # Run all scrapers concurrently
        tasks = [scraper.search(context, query) for scraper in scrapers]

        # Use gather but catch exceptions individually to not fail all
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for res in responses:
            if isinstance(res, list):
                results.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Scraper failed with error: {res}")

        await context.close()
        await browser.close()

    # Deduplicate by magnet link
    unique_results: list[dict[str, Any]] = []
    seen_magnets: set[str] = set()

    for r in results:
        magnet = r.get("magnet")
        if magnet and magnet not in seen_magnets:
            unique_results.append(r)
            seen_magnets.add(magnet)

    logger.info(
        "Search completed for '%s'. Found %d unique magnet(s).",
        query,
        len(unique_results),
    )
    return unique_results
