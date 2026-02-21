from .base import BaseScraper
from .filmes_torrent import FilmesTorrentScraper
from .pirate_bay import PirateBayScraper
from .leetx import LeetXScraper
from .yts import YTSScraper
from .kickass import KickassTorrentsScraper
from .redetorrent import RedeTorrentScraper
from .apache import ApacheTorrentScraper
from .btdigg import BTDiggScraper

__all__ = [
    "BaseScraper",
    "FilmesTorrentScraper",
    "PirateBayScraper",
    "LeetXScraper",
    "YTSScraper",
    "KickassTorrentsScraper",
    "RedeTorrentScraper",
    "ApacheTorrentScraper",
    "BTDiggScraper"
]
