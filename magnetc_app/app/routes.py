import asyncio
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from .scraper import search_movie


def register_routes(app: Flask) -> None:
    """
    Registra todas as rotas da aplicação.
    """

    @app.get("/")
    def index():
        # Renderiza o HTML principal
        return render_template("index.html")

    @app.post("/api/search")
    def api_search():
        """
        Endpoint de busca.
        Recebe JSON: { "query": "nome do filme" }
        Retorna JSON: { "results": [...] } ou { "error": "..." }
        """
        data = request.get_json(silent=True) or {}
        query: str = (data.get("query") or "").strip()

        if not query:
            return jsonify({"error": "Missing query."}), 400

        try:
            # Chama a função async usando asyncio.run (ok para uso simples)
            results: List[Dict[str, Any]] = asyncio.run(search_movie(query))
            return jsonify({"results": results})
        except Exception as exc:  # noqa: BLE001
            app.logger.error("Error while searching '%s': %s", query, exc)
            return jsonify({"error": "Internal server error"}), 500
