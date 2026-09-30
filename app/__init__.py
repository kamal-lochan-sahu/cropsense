"""CropSense - AI-assisted crop recommendation."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, request
from werkzeug.exceptions import HTTPException, InternalServerError

from .config import Config
from .ml.predictor import Predictor
from .routes import API_PATHS, bp
from .services.guides import GuideService

logger = logging.getLogger(__name__)


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    predictor = Predictor(app.config["MODEL_PATH"])
    app.extensions["predictor"] = predictor
    app.extensions["guides"] = GuideService(
        api_key=app.config["GROQ_API_KEY"],
        models=[app.config["GROQ_MODEL"], *app.config["GROQ_FALLBACK_MODELS"]],
        url=app.config["GROQ_URL"],
        timeout=app.config["GROQ_TIMEOUT"],
        cache_size=app.config["GUIDE_CACHE_SIZE"],
        allowed_crops=predictor.classes,
    )

    app.register_blueprint(bp)
    _register_error_handlers(app)
    _register_security_headers(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        if request.path in API_PATHS:
            name = (exc.name or "error").lower().replace(" ", "_")
            return {"error": name}, exc.code
        return exc

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        logger.exception("unhandled error on %s %s", request.method, request.path)
        if request.path in API_PATHS:
            return {"error": "internal_server_error"}, 500
        return InternalServerError()


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=(self)"
        )
        return response


def __getattr__(name: str):
    # Lets `gunicorn app:app` keep working without building the app at import time.
    if name == "app":
        instance = create_app()
        globals()["app"] = instance
        return instance
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
