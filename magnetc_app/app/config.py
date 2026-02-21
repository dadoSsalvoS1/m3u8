import logging


class Config:
    # URL base do site onde vamos pesquisar
    SEARCH_URL: str = "https://filmestorrent.top/"

    # User-agent “realista” pra parecer browser
    MAGNET_SITE_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )

    # Palavras-chave que indicam boa qualidade
    QUALITY_KEYWORDS: list[str] = ["1080p", "720p", "x264", "DUAL", "5.1"]

    # Limite de páginas internas visitadas por busca (protege o site e sua máquina)
    MAX_DETAIL_PAGES: int = 30

    # Logging
    LOG_LEVEL: int = logging.INFO


def configure_logging(level: int = Config.LOG_LEVEL) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("magnet_search_app")
    return logger
