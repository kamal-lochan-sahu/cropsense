"""CropSense - AI-assisted crop recommendation."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from flask import Flask, request
from werkzeug.exceptions import HTTPException, InternalServerError

from .config import Config
from .ml.advice import Advisor
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
    app.extensions["advisor"] = Advisor(app.config["CROP_PROFILES_PATH"], predictor.classes)
    app.extensions["guides"] = GuideService(
        api_key=app.config["GROQ_API_KEY"],
        models=[app.config["GROQ_MODEL"], *app.config["GROQ_FALLBACK_MODELS"]],
        url=app.config["GROQ_URL"],
        timeout=app.config["GROQ_TIMEOUT"],
        cache_size=app.config["GUIDE_CACHE_SIZE"],
        allowed_crops=predictor.classes,
    )

    app.config.setdefault("ASSET_VERSION", _asset_version(app))

    @app.context_processor
    def inject_asset_version():
        return {"asset_version": app.config["ASSET_VERSION"]}

    app.register_blueprint(bp)
    _register_error_handlers(app)
    _register_security_headers(app)
    return app


def _asset_version(app: Flask) -> str:
    """Short hash of the front-end files; changes whenever they do, busting caches."""
    root = Path(app.root_path)
    files = sorted(
        [*(root / "static" / "css").glob("*.css"), *(root / "static" / "js").glob("*.js")]
        + [root / "static" / "manifest.json", root / "templates" / "sw.js"]
    )
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:10]


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


CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "connect-src 'self' https://ipapi.co",
        "manifest-src 'self'",
        "worker-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        if request.path in API_PATHS:
            headers.setdefault("Cache-Control", "no-store")
        return response


def __getattr__(name: str):
    # Lets `gunicorn app:app` keep working without building the app at import time.
    if name == "app":
        instance = create_app()
        globals()["app"] = instance
        return instance
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
