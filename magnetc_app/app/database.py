import sqlite3
import json
import logging
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("magnet_search_app")

class DatabaseManager:
    DB_NAME = "magnetc.db"
    _lock = threading.Lock()

    def __init__(self):
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.DB_NAME, check_same_thread=False)

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Scans table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_type TEXT,  -- 'manual' or 'scheduled'
                    status TEXT,     -- 'pending', 'running', 'completed', 'failed'
                    filters TEXT,    -- JSON string of filters
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    schedule_interval TEXT -- 'once', 'hourly', 'daily' etc.
                )
            ''')

            # Results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    title TEXT,
                    magnet TEXT,
                    url TEXT,
                    quality TEXT,
                    info_text TEXT,
                    source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(magnet) -- Prevent duplicates globally or per scan? Globally is better for "all elements"
                )
            ''')

            # Discovered Sites table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE,
                    name TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    type TEXT DEFAULT 'generic', -- 'specific' or 'generic'
                    last_success TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Seed default sites
            default_sites = [
                ("https://yts.rs", "YTS", "specific"),
                ("https://1337x.to", "1337x", "specific"),
                ("https://thepiratebay.org", "ThePirateBay", "specific"),
                ("https://filmestorrent.top", "FilmesTorrent", "specific"),
                ("https://kickasstorrents.cr", "KickassTorrents", "specific"),
                ("https://redetorrent.com", "RedeTorrent", "specific"),
                ("https://apachetorrent.com", "ApacheTorrent", "specific"),
                ("https://btdig.com", "BTDigg", "specific"),
            ]

            for url, name, type_ in default_sites:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO sites (domain, name, type) VALUES (?, ?, ?)",
                        (url, name, type_)
                    )
                except Exception:
                    pass

            conn.commit()
            conn.close()

    def create_scan(self, scan_type: str, filters: Dict[str, Any], schedule_interval: str = "once") -> int:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scans (scan_type, status, filters, schedule_interval) VALUES (?, ?, ?, ?)",
                (scan_type, "pending", json.dumps(filters), schedule_interval)
            )
            scan_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return scan_id

    def update_scan_status(self, scan_id: int, status: str):
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE scans SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, scan_id)
            )
            conn.commit()
            conn.close()

    def save_results(self, scan_id: int, results: List[Dict[str, Any]]) -> int:
        count = 0
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            for r in results:
                try:
                    qualities = r.get("qualities", [])
                    quality_str = ", ".join(qualities) if isinstance(qualities, list) else str(qualities)

                    cursor.execute('''
                        INSERT OR IGNORE INTO scan_results (scan_id, title, magnet, url, quality, info_text, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        scan_id,
                        r.get("title", "Unknown"),
                        r.get("magnet"),
                        r.get("url"),
                        quality_str,
                        r.get("info_text", ""),
                        r.get("source", "Unknown")
                    ))
                    if cursor.rowcount > 0:
                        count += 1
                except Exception as e:
                    logger.error(f"Failed to save result: {e}")

            conn.commit()
            conn.close()
        return count

    def get_scans(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scans ORDER BY created_at DESC LIMIT 50")
            rows = cursor.fetchall()
            scans = [dict(row) for row in rows]
            conn.close()
            # Parse filters JSON
            for s in scans:
                try:
                    s['filters'] = json.loads(s['filters'])
                except:
                    pass
            return scans

    def get_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scan_results ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()
            return results

    def get_active_sites(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sites WHERE is_active = 1")
            rows = cursor.fetchall()
            sites = [dict(row) for row in rows]
            conn.close()
            return sites

    def add_discovered_site(self, url: str) -> bool:
        with self._lock:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = f"{parsed.scheme}://{parsed.netloc}"
                name = parsed.netloc.replace("www.", "").split(".")[0].capitalize()

                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sites (domain, name, type) VALUES (?, ?, 'generic')",
                    (domain, name)
                )
                conn.commit()
                conn.close()
                return True
            except sqlite3.IntegrityError:
                return False # Already exists
            except Exception as e:
                logger.error(f"Failed to add site {url}: {e}")
                return False

db = DatabaseManager()
