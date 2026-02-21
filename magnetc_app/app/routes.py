import asyncio
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from .scraper import search_movie
from .database import db
from .scheduler import schedule_scan, start_scheduler


def register_routes(app: Flask) -> None:
    """
    Registra todas as rotas da aplicação.
    """

    # Start scheduler when routes are registered (app startup)
    start_scheduler()

    @app.get("/")
    def index():
        # Renderiza o HTML principal
        return render_template("index.html")

    @app.post("/api/search")
    def api_search():
        """
        Endpoint de busca.
        Recebe JSON: { "query": "nome do filme", "search_type": "title"|"actor" }
        Retorna JSON: { "results": [...] } ou { "error": "..." }
        """
        data = request.get_json(silent=True) or {}
        query: str = (data.get("query") or "").strip()
        search_type: str = data.get("search_type", "title")

        if not query:
            return jsonify({"error": "Missing query."}), 400

        try:
            # Chama a função async usando asyncio.run (ok para uso simples)
            results: List[Dict[str, Any]] = asyncio.run(search_movie(query, search_type=search_type))
            return jsonify({"results": results})
        except Exception as exc:  # noqa: BLE001
            app.logger.error("Error while searching '%s': %s", query, exc)
            return jsonify({"error": "Internal server error"}), 500

    @app.post("/api/scan/start")
    def start_scan_endpoint():
        """
        Starts a background scan job.
        JSON: { "site": "YTS", "filters": {...}, "interval": "once" }
        """
        data = request.get_json(silent=True) or {}
        site = data.get("site", "YTS")
        filters = data.get("filters", {})
        interval = data.get("interval", "once")

        # Add site to filters for scheduler usage
        filters['site'] = site

        scan_id = schedule_scan("manual_browse", filters, interval)
        return jsonify({"message": "Scan started", "scan_id": scan_id})

    @app.get("/api/scan/jobs")
    def get_jobs():
        """Returns list of recent scans/jobs."""
        scans = db.get_scans()
        # Convert rows to dicts is handled in db manager
        return jsonify({"jobs": scans})

    @app.get("/api/scan/results")
    def get_scan_results():
        """Returns collected results."""
        limit = request.args.get("limit", 100, type=int)
        results = db.get_results(limit)
        return jsonify({"results": results})
