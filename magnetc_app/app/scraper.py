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
    ApacheTorrentScraper,
)
from .scrapers.generic import GenericScraper
from .exceptions import CloudflareBlocked
from .database import db
from .discovery import discovery
from playwright._impl._errors import TargetClosedError

logger = configure_logging()

# Global config for headless mode, can be set by app factory or run.py
HEADLESS_MODE = True

def set_headless_mode(headless: bool):
    global HEADLESS_MODE
    HEADLESS_MODE = headless

def load_scrapers_from_db() -> list:
    """
    Loads active sites from DB and returns scraper instances.
    Maps known domains to specific classes, otherwise uses GenericScraper.
    """
    active_sites = db.get_active_sites()
    scrapers = []

    # Map domain (normalized) to class
    # Helper to clean domain for matching
    def clean_domain(d):
        return d.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]

    domain_map = {
        clean_domain(YTSScraper.BASE_URL): YTSScraper,
        clean_domain(PirateBayScraper.BASE_URL): PirateBayScraper,
        clean_domain(LeetXScraper.BASE_URL): LeetXScraper,
        clean_domain(FilmesTorrentScraper.BASE_URL): FilmesTorrentScraper,
        clean_domain(KickassTorrentsScraper.BASE_URL): KickassTorrentsScraper,
        clean_domain(RedeTorrentScraper.BASE_URL): RedeTorrentScraper,
        clean_domain(ApacheTorrentScraper.BASE_URL): ApacheTorrentScraper,
    }

    for site in active_sites:
        domain = site['domain']
        name = site['name']
        cleaned = clean_domain(domain)

        if cleaned in domain_map:
            scrapers.append(domain_map[cleaned]())
        else:
            # Check if generic scraper already handles it (prevent duplicates if DB has it)
            scrapers.append(GenericScraper(domain, name=name))

    return scrapers

async def search_movie(
    query: str,
    *,
    search_url: str | None = None,
    quality_keywords: list[str] | None = None,
    max_detail_pages: int | None = None,
    search_type: str = "title" # 'title' or 'actor'
) -> List[Dict[str, Any]]:
    """
    Orchestrate search across multiple torrent sites.
    If search_type is 'actor', enables deep web discovery.
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
        logger.info(f"Starting search for query: '{query}' (Type: {search_type}, Attempt {attempt}/{max_attempts}, Headless: {current_headless_mode})")

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

            # Load scrapers dynamically from DB
            scrapers = load_scrapers_from_db()

            tasks = [scraper.search(context, query) for scraper in scrapers]

            # If Actor/Deep Scan mode, add discovery task
            if search_type == "actor":
                tasks.append(discovery.discover_and_scrape(context, query))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for res in responses:
                if isinstance(res, list):
                    results.extend(res)
                elif isinstance(res, CloudflareBlocked):
                    logger.warning(f"Cloudflare challenge detected: {res}")
                    if current_headless_mode:
                        needs_retry_headed = True
                elif isinstance(res, TargetClosedError):
                    logger.warning("Browser window was closed manually by user or system.")
                elif isinstance(res, Exception):
                    logger.error(f"Scraper failed with error: {res}")

            try:
                await context.close()
                await browser.close()
            except Exception:
                pass

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
