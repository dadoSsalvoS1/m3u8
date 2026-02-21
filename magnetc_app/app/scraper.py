import re
import asyncio
from typing import Any, Dict, List

from playwright.async_api import async_playwright, Page

from .config import Config, configure_logging


logger = configure_logging()


async def _extract_external_urls_from_search_page(page: Page) -> list[str]:
    """
    A partir da página de resultados, encontra TODOS os botões com onclick
    que apontam para páginas internas / externas relevantes.
    """
    detail_buttons = await page.locator("button").all()
    external_urls: set[str] = set()

    for btn in detail_buttons:
        onclick_text = await btn.get_attribute("onclick")
        if not onclick_text:
            continue

        # window.open('URL') ou location.href='URL'
        match = re.search(r"window\.open\('([^']+)'", onclick_text)
        if not match:
            match = re.search(r"location\.href\s*=\s*'([^']+)'", onclick_text)

        if match:
            external_urls.add(match.group(1))

    urls = list(external_urls)
    logger.info("Found %d possible result pages.", len(urls))
    return urls


async def _extract_magnets_from_detail_page(
    page: Page,
    url: str,
    quality_keywords: list[str],
) -> list[dict[str, Any]]:
    """
    Abre uma página de detalhe e faz uma varredura geral em botões
    procurando magnet links e informações de qualidade.
    """
    results: list[dict[str, Any]] = []

    try:
        await page.goto(url, timeout=60000)
        await asyncio.sleep(0.2)  # pequeno delay pra carregar scripts

        all_buttons = await page.locator("button").all()
        found_magnets: list[dict[str, Any]] = []

        for b in all_buttons:
            b_text = (await b.inner_text() or "").strip().lower()

            magnet = await b.get_attribute("data-magnet")
            if not magnet:
                magurl = await b.get_attribute("data-url")
                if magurl and magurl.startswith("magnet:"):
                    magnet = magurl

            if not magnet:
                onclick = await b.get_attribute("onclick")
                if onclick and "magnet:" in onclick:
                    found = re.search(r"(magnet:\?xt=[^'\" ]+)", onclick)
                    if found:
                        magnet = found.group(1)

            if not magnet or not magnet.startswith("magnet:"):
                continue

            info_text = ""
            info_divs = page.locator("div.download-info")
            if await info_divs.count() > 0:
                info_text = await info_divs.first.inner_text()
            else:
                # fallback: usa parte do conteúdo da página
                info_text = (await page.content())[:3000]  # limita tamanho

            quality_match = [
                k
                for k in quality_keywords
                if k.lower() in info_text.lower() or k.lower() in b_text
            ]

            title = await page.title()
            found_magnets.append(
                {
                    "title": title.replace(" - Filmes Torrent", "").strip(),
                    "url": url,
                    "qualities": quality_match,
                    "info_text": info_text,
                    "magnet": magnet,
                }
            )

        if found_magnets:
            logger.info(
                "Found %d magnet link(s) in page '%s'", len(found_magnets), url
            )
            results.extend(found_magnets)
        else:
            logger.info("No magnet link found in %s", url)

    except Exception as exc:
        logger.warning("Failed on %s: %s", url, exc)

    return results


async def search_movie(
    query: str,
    *,
    search_url: str | None = None,
    quality_keywords: list[str] | None = None,
    max_detail_pages: int | None = None,
) -> List[Dict[str, Any]]:
    """
    Função principal de busca de filmes.

    Retorna uma lista de dicionários com:
      - title
      - url
      - qualities
      - info_text
      - magnet
    """
    if not query or not query.strip():
        return []

    search_url = search_url or Config.SEARCH_URL
    quality_keywords = quality_keywords or Config.QUALITY_KEYWORDS
    max_detail_pages = max_detail_pages or Config.MAX_DETAIL_PAGES

    logger.info("Starting search for query: '%s'", query)

    results: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=Config.MAGNET_SITE_USER_AGENT)
        page = await context.new_page()

        try:
            logger.info("Navigating to: %s", search_url)
            await page.goto(search_url, timeout=60000)

            # Campo de busca
            search_input = page.locator('input[name="s"].search')
            await search_input.wait_for()
            await search_input.fill(query)
            await search_input.press("Enter")

            # Mensagem de resultado
            await page.wait_for_selector("p.search-msg", timeout=60000)
            search_msg = await page.locator("p.search-msg").inner_text()
            logger.info("Site response: %s", search_msg)

            if "Resultado da pesquisa para:" not in search_msg:
                logger.warning("No results found or search failed")
                return []

            # Descobre as páginas de detalhe
            external_urls = await _extract_external_urls_from_search_page(page)
            external_urls = external_urls[:max_detail_pages]

            # Varre cada página e extrai magnets
            for url in external_urls:
                page_results = await _extract_magnets_from_detail_page(
                    page,
                    url,
                    quality_keywords,
                )
                results.extend(page_results)

        finally:
            await browser.close()

    # Remove duplicados por magnet
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
