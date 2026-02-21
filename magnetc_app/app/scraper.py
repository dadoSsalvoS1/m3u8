import asyncio
from typing import Any, Dict, List

from playwright.async_api import async_playwright

from .config import Config, configure_logging
from .scrapers import (
    FilmesTorrentScraper,
    PirateBayScraper,
    LeetXScraper,
    YTSScraper,
    KickassTorrentsScraper,
    RedeTorrentScraper,
    ApacheTorrentScraper
)
from .exceptions import CloudflareBlocked

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

    # Local attempt control
    attempt = 1
    # If headless is False globally, we don't need to retry as headed.
    max_attempts = 2 if HEADLESS_MODE else 1

    current_headless_mode = HEADLESS_MODE
    results: list[dict[str, Any]] = []

    while attempt <= max_attempts:
        logger.info(f"Starting search for query: '{query}' (Attempt {attempt}/{max_attempts}, Headless: {current_headless_mode})")

        # We start fresh on each attempt to avoid partial duplicates or mixed states
        results = []
        needs_retry_headed = False

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=current_headless_mode,
                args=["--disable-blink-features=AutomationControlled"],
            )
            # Increase default navigation timeout when headed to allow CAPTCHA solving
            default_timeout = 90000 if not current_headless_mode else 30000

            # Use random User-Agent for better stealth
            user_agent = Config.get_random_user_agent()

            context = await browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1280, "height": 720},
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                locale="en-US",
                timezone_id="America/New_York", # Common timezone
            )
            context.set_default_timeout(default_timeout)

            scrapers = [
                FilmesTorrentScraper(),
                PirateBayScraper(),
                LeetXScraper(),
                YTSScraper(),
                KickassTorrentsScraper(),
                RedeTorrentScraper(),
                ApacheTorrentScraper(),
            ]

            tasks = [scraper.search(context, query) for scraper in scrapers]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for res in responses:
                if isinstance(res, list):
                    results.extend(res)
                elif isinstance(res, CloudflareBlocked):
                    logger.warning(f"Cloudflare challenge detected: {res}")
                    if current_headless_mode:
                        needs_retry_headed = True
                elif isinstance(res, Exception):
                    logger.error(f"Scraper failed with error: {res}")

            await context.close()
            await browser.close()

        # Retry logic
        if needs_retry_headed and attempt < max_attempts:
            logger.warning("Cloudflare blocked scraping. Switching to HEADED mode for manual verification/solving...")
            current_headless_mode = False
            attempt += 1
            await asyncio.sleep(2)
            continue

        break

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
