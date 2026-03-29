from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import asyncio
import logging
import threading

from app.scraper import search_movie
from app.database import db
from app.config import Config
from app.scrapers import YTSScraper

# We need to import all scrapers if we want to support browsing them all
# For now, we support YTS browsing as implemented.

logger = logging.getLogger("magnet_search_app")

scheduler = BackgroundScheduler()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def _run_async_scan(scan_id: int, scan_type: str, filters: dict):
    """
    Wrapper to run the async scan logic in a sync thread for APScheduler.
    """
    logger.info(f"Starting scan job {scan_id} ({scan_type})")
    db.update_scan_status(scan_id, "running")

    try:
        # We need a new event loop for this thread if it doesn't have one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Determine what to do based on scan_type
        # If 'search', we use search_movie
        # If 'browse', we use scraper.browse

        if scan_type == 'manual_browse':
            site = filters.get('site', 'YTS')
            # Instantiate scraper based on site name
            # Ideally use a factory, but hardcoding YTS for now as MVP
            if site == 'YTS':
                scraper = YTSScraper()

                # We need a browser context just like in search_movie
                from playwright.async_api import async_playwright

                async def run_browse():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(
                            headless=True, # Always headless for background jobs
                            args=["--disable-blink-features=AutomationControlled"]
                        )
                        context = await browser.new_context(user_agent=Config.get_random_user_agent())

                        results = await scraper.browse(context, "movies", filters)

                        await context.close()
                        await browser.close()
                        return results

                results = loop.run_until_complete(run_browse())
                saved_count = db.save_results(scan_id, results)
                logger.info(f"Scan {scan_id} completed. Saved {saved_count} items.")
                db.update_scan_status(scan_id, "completed")
            else:
                logger.warning(f"Site {site} not supported for browsing yet.")
                db.update_scan_status(scan_id, "failed")

        else:
            # Default search behavior (not implemented for browse tab but good for future)
            pass

        loop.close()

    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        db.update_scan_status(scan_id, "failed")

def schedule_scan(scan_type: str, filters: dict, interval: str = "once"):
    """
    Schedules a scan.
    :param interval: 'once', 'hourly', 'daily'
    """
    scan_id = db.create_scan(scan_type, filters, interval)

    if interval == "once":
        # Run immediately (or slightly delayed)
        run_date = datetime.now() + timedelta(seconds=2)
        scheduler.add_job(
            _run_async_scan,
            trigger=DateTrigger(run_date=run_date),
            args=[scan_id, scan_type, filters],
            id=f"scan_{scan_id}",
            name=f"Scan {scan_id}"
        )
    elif interval == "hourly":
        scheduler.add_job(
            _run_async_scan,
            trigger=IntervalTrigger(hours=1),
            args=[scan_id, scan_type, filters],
            id=f"scan_{scan_id}",
            name=f"Scan {scan_id} (Hourly)"
        )
    elif interval == "daily":
        scheduler.add_job(
            _run_async_scan,
            trigger=IntervalTrigger(days=1),
            args=[scan_id, scan_type, filters],
            id=f"scan_{scan_id}",
            name=f"Scan {scan_id} (Daily)"
        )

    return scan_id
