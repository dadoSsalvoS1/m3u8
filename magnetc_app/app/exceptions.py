class CloudflareBlocked(Exception):
    """Raised when a scraper detects a Cloudflare challenge page."""
    pass

class NavigationTimeout(Exception):
    """Raised when a scraper times out loading a page."""
    pass
