from app import create_app
from app.scraper import set_headless_mode

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Movie Magnet Search Web App")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8100, type=int)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--headed", action="store_true", help="Run browser in visible mode (for debugging/CAPTCHA)")
    args = parser.parse_args()

    # Configure headless mode globally
    # If --headed is passed, headless=False
    set_headless_mode(not args.headed)

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
