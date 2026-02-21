from app import create_app
from app.scraper import set_headless_mode
from app.config import Config

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Movie Magnet Search Web App")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8100, type=int)
    parser.add_argument("--debug", action="store_true")
    # Changed semantics: now default is headed (Config.HEADLESS_DEFAULT=False), so we might want a flag to force headless
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (hidden)")
    args = parser.parse_args()

    # Logic:
    # If Config.HEADLESS_DEFAULT is False (Headed), then args.headless True makes it True.
    # If we want to respect the user's wish to "remove headless mode", we ensure the default without args is Headed.

    is_headless = args.headless if args.headless else Config.HEADLESS_DEFAULT
    set_headless_mode(is_headless)

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
