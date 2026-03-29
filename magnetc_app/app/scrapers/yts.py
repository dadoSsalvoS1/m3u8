import asyncio
import json
import urllib.parse
from typing import Any, Dict, List

from playwright.async_api import BrowserContext

from app.config import configure_logging
from .base import BaseScraper

logger = configure_logging()


class YTSScraper(BaseScraper):
    name = "YTS"
    BASE_URL = "https://yts.rs"  # Mirror seems to work better

    # Standard YTS trackers to ensure magnet links work well
    TRACKERS = [
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.openbittorrent.com:80",
        "udp://tracker.coppersurfer.tk:6969",
        "udp://glotorrents.pw:6969/announce",
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.leechers-paradise.org:6969",
        "udp://p4p.arenabg.com:1337",
        "udp://9.rarbg.to:2710/announce",
    ]

    async def search(self, context: BrowserContext, query: str) -> List[Dict[str, Any]]:
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        # YTS search URL (using mirror)
        # We need to URL encode the query
        encoded_query = urllib.parse.quote(query)
        search_url = f"{self.BASE_URL}/browse-movies/{encoded_query}"

        try:
            logger.info(f"[{self.name}] Navigating to: {search_url}")
            try:
                await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Try to extract data from Next.js hydration script
            try:
                # Wait a bit for the script to be present
                await page.wait_for_selector("#__NEXT_DATA__", state="attached", timeout=10000)

                data_content = await page.locator("#__NEXT_DATA__").inner_text()
                data = json.loads(data_content)

                movies = data.get("props", {}).get("pageProps", {}).get("movies", []) or []

                if not movies:
                    # Fallback or just empty
                    logger.info(f"[{self.name}] No movies found in JSON data.")

                    # Check if text says "No YIFY Movies Found" to confirm it's not an error
                    content = await page.content()
                    if "No YIFY Movies Found" not in content and "Movies Found" not in content:
                        logger.warning(f"[{self.name}] Possible layout change or block.")
                    return []

                logger.info(f"[{self.name}] Found {len(movies)} movies in JSON. Processing...")

                for movie in movies:
                    results.extend(self._parse_movie_data(movie))

            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract/parse JSON data: {e}")
                # Fallback to HTML scraping could be added here, but JSON is much better if available.

        except Exception as e:
            logger.error(f"[{self.name}] Error during search: {e}")
        finally:
            await page.close()

        return results

    async def browse(self, context: BrowserContext, category: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Browses YTS with filters.
        YTS Browse URL: /browse-movies/TERM/QUALITY/GENRE/RATING/ORDER/YEAR
        Note: The URL structure might vary by mirror, but standard is:
        /browse-movies/{term}/{quality}/{genre}/{rating}/{order}/{year}

        Example: /browse-movies/0/all/action/0/latest/2023
        """
        page = await context.new_page()
        results: list[dict[str, Any]] = []

        # Parse filters
        term = "0" # Default for all
        quality = "all"
        genre = filters.get("genre", "all").lower()
        rating = "0"
        order = filters.get("sort", "latest").lower() # latest, oldest, seeds, peers, year, rating, likes, alphabetical, downloads

        # Year filter is tricky. YTS URL usually supports only one year or min/max via API?
        # Web UI structure usually supports 'year' as single value or range?
        # Let's check typical URL: https://yts.mx/browse-movies/0/all/all/0/latest/2024
        # It seems to support single year or range if supported by backend but URL usually takes one param.
        # We will iterate if a range is provided? Or just ignore year if range is too wide.

        year = "0"
        year_from = filters.get("year_from")
        year_to = filters.get("year_to")

        # If year range is specific, we might need to iterate.
        # For this MVP, let's assume we search for the 'year_from' if set, or just 0.
        if year_from:
            year = str(year_from)

        browse_url = f"{self.BASE_URL}/browse-movies/{term}/{quality}/{genre}/{rating}/{order}/{year}"

        try:
            logger.info(f"[{self.name}] Browsing: {browse_url}")
            try:
                await page.goto(browse_url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to load URL: {e}")
                return []

            # Extract via JSON (same logic as search)
            try:
                await page.wait_for_selector("#__NEXT_DATA__", state="attached", timeout=10000)
                data_content = await page.locator("#__NEXT_DATA__").inner_text()
                data = json.loads(data_content)

                movies = data.get("props", {}).get("pageProps", {}).get("movies", []) or []

                logger.info(f"[{self.name}] Found {len(movies)} movies in browse scan.")

                # Check for year filtering if range provided
                filtered_count = 0
                for movie in movies:
                    movie_year = movie.get("year", 0)
                    if year_from and movie_year < int(year_from):
                        continue
                    if year_to and movie_year > int(year_to):
                        continue

                    parsed = self._parse_movie_data(movie)
                    results.extend(parsed)
                    filtered_count += 1

                logger.info(f"[{self.name}] Filtered down to {filtered_count} movies based on criteria.")

            except Exception as e:
                logger.warning(f"[{self.name}] Failed to extract browse data: {e}")

        except Exception as e:
            logger.error(f"[{self.name}] Error during browse: {e}")
        finally:
            await page.close()

        return results

    def _parse_movie_data(self, movie: dict) -> List[Dict[str, Any]]:
        """Helper to parse a single movie object from YTS JSON."""
        parsed_results = []
        title = movie.get("title_long") or movie.get("title") or "Unknown Title"
        slug = movie.get("slug")
        movie_url = f"{self.BASE_URL}/movie/{slug}" if slug else self.BASE_URL
        description = movie.get("description_full") or movie.get("summary") or ""

        torrents = movie.get("torrents", [])
        for torrent in torrents:
            hash_str = torrent.get("hash")
            if not hash_str:
                continue

            quality = torrent.get("quality", "unknown")
            torrent_type = torrent.get("type", "")
            size = torrent.get("size", "")

            dn = urllib.parse.quote(title)
            tr_params = "&".join([f"tr={urllib.parse.quote(t)}" for t in self.TRACKERS])
            magnet_link = f"magnet:?xt=urn:btih:{hash_str}&dn={dn}&{tr_params}"

            qualities = [quality]
            if torrent_type:
                qualities.append(torrent_type)

            info_text = f"Size: {size}. Year: {movie.get('year')}. {description}"

            parsed_results.append({
                "title": f"{title} [{quality}]",
                "url": movie_url,
                "qualities": qualities,
                "info_text": info_text[:300],
                "magnet": magnet_link,
                "source": self.name
            })
        return parsed_results
