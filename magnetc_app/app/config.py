import logging
import random


class Config:
    # URL base do site onde vamos pesquisar
    SEARCH_URL: str = "https://filmestorrent.top/"

    # Default User-Agent
    MAGNET_SITE_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )

    # List of realistic User-Agents for rotation
    USER_AGENTS: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/122.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
    ]

    # Palavras-chave que indicam boa qualidade
    QUALITY_KEYWORDS: list[str] = ["1080p", "720p", "x264", "DUAL", "5.1"]

    # Limite de páginas internas visitadas por busca (protege o site e sua máquina)
    MAX_DETAIL_PAGES: int = 30

    # Logging
    LOG_LEVEL: int = logging.INFO

    # App Settings
    HEADLESS_DEFAULT: bool = False # Default to Headed mode as requested

    @classmethod
    def get_random_user_agent(cls) -> str:
        """Returns a random user-agent from the list."""
        return random.choice(cls.USER_AGENTS)


def configure_logging(level: int = Config.LOG_LEVEL) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("magnet_search_app")
    return logger
