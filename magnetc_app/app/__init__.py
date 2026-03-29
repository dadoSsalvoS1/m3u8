from flask import Flask
from flask_cors import CORS

from .config import Config
from .routes import register_routes


def create_app(config_class: type[Config] = Config) -> Flask:
    """
    Application factory. Creates and configures the Flask app instance.
    """
    app = Flask(
        __name__,
        static_folder="../static",
        template_folder="../templates",
    )
    app.config.from_object(config_class)

    # Enable CORS if you quiser no futuro separar front e back
    CORS(app)

    # Register blueprints / routes
    register_routes(app)

    return app
