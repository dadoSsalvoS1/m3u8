from app import create_app

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Movie Magnet Search Web App")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8100, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
