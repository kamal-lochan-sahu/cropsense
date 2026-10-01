"""HTTP routes."""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)

from .services.guides import GuideError
from .validation import ValidationError, parse_features

bp = Blueprint("main", __name__)

API_PATHS = frozenset({"/predict", "/crop-guide", "/health"})


def _error(message: str, status: int, **extra):
    return jsonify({"error": message, **extra}), status


@bp.get("/")
def home():
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.get("/sw.js")
def service_worker():
    # Served from the site root so the worker's scope covers the whole app.
    response = make_response(render_template("sw.js"))
    response.mimetype = "application/javascript"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@bp.get("/favicon.ico")
def favicon():
    icons = current_app.static_folder + "/icons"
    return send_from_directory(icons, "favicon-32.png", mimetype="image/png")


@bp.get("/health")
def health():
    return jsonify(
        status="ok",
        model_loaded=True,
        guides_configured=current_app.extensions["guides"].configured,
    )


@bp.post("/predict")
def predict():
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return _error("invalid JSON body", 400)

    try:
        values, warnings = parse_features(payload)
    except ValidationError as exc:
        return _error("validation_failed", 422, fields=exc.errors)

    result = current_app.extensions["predictor"].predict(values)
    if warnings:
        result["warnings"] = warnings
    return jsonify(result)


@bp.post("/crop-guide")
def crop_guide():
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return _error("invalid JSON body", 400)

    crop = payload.get("crop")
    lang = payload.get("lang", "en")
    if not isinstance(crop, str) or not isinstance(lang, str):
        return _error("crop and lang must be strings", 400)

    try:
        guide, cached = current_app.extensions["guides"].get(crop, lang)
    except GuideError as exc:
        return _error(exc.message, exc.status)
    return jsonify(guide=guide, cached=cached)
