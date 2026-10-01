import json
import re
from pathlib import Path

import pytest

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"


def static_urls(text):
    """All /static/... URLs referenced in a document, without query strings."""
    return sorted({m.split("?")[0] for m in re.findall(r"""["'(](/static/[^"')\s]+)""", text)})


def test_every_static_url_in_html_resolves(client):
    html = client.get("/").get_data(as_text=True)
    urls = static_urls(html)
    assert "/static/css/style.css" in urls and "/static/js/app.js" in urls
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_manifest_icons_resolve(client):
    manifest = client.get("/static/manifest.json").get_json()
    assert manifest["scope"] == "/" and manifest["start_url"] == "/"
    purposes = {icon["purpose"] for icon in manifest["icons"]}
    assert {"any", "maskable"} <= purposes
    for icon in manifest["icons"]:
        assert client.get(icon["src"]).status_code == 200, icon["src"]


def test_social_image_and_apple_icon_exist(client):
    html = client.get("/").get_data(as_text=True)
    assert "/static/img/og-image.png" in html
    assert client.get("/static/img/og-image.png").status_code == 200
    assert client.get("/static/icons/apple-touch-icon.png").status_code == 200


def test_favicon_ico_route(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_html_is_csp_safe(client):
    html = client.get("/").get_data(as_text=True)
    assert not re.search(r"\son[a-z]+\s*=", html), "inline event handler found"
    assert "style=" not in html, "inline style attribute found"
    assert not re.search(r"<script(?![^>]*\bsrc=)", html), "inline script found"


def test_csp_header_blocks_inline_code(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "unsafe-inline" not in csp and "unsafe-eval" not in csp
    assert "frame-ancestors 'none'" in csp


def test_service_worker_is_served_from_root_scope(app, client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.mimetype == "application/javascript"
    assert response.headers["Service-Worker-Allowed"] == "/"
    assert response.headers["Cache-Control"] == "no-cache"
    body = response.get_data(as_text=True)
    assert app.config["ASSET_VERSION"] in body
    assert "{{" not in body


def test_asset_version_is_a_short_hash(app):
    assert re.fullmatch(r"[0-9a-f]{10}", app.config["ASSET_VERSION"])


def test_html_and_assets_use_the_same_version(app, client):
    version = app.config["ASSET_VERSION"]
    html = client.get("/").get_data(as_text=True)
    assert f"/static/js/app.js?v={version}" in html
    assert f"/static/css/style.css?v={version}" in html


def test_html_is_not_cached_but_api_is_no_store(client, valid_payload):
    assert client.get("/").headers["Cache-Control"] == "no-cache"
    assert client.post("/predict", json=valid_payload).headers["Cache-Control"] == "no-store"
    assert client.get("/health").headers["Cache-Control"] == "no-store"


def english_keys():
    source = (STATIC / "js" / "translations.js").read_text(encoding="utf-8")
    block = source[source.index("  en: {") : source.index("/* ── Indian")]
    return set(re.findall(r"\b([a-z_]+):\s*[\"']", block))


def test_html_i18n_keys_exist_in_english(client):
    html = client.get("/").get_data(as_text=True)
    used = set(re.findall(r'data-i18n(?:-aria)?="([a-z_]+)"', html))
    assert used, "no data-i18n attributes found"
    assert used <= english_keys(), used - english_keys()


def test_app_js_only_uses_known_translation_keys():
    source = (STATIC / "js" / "app.js").read_text(encoding="utf-8")
    used = set(re.findall(r"\bt\('([a-z_]+)'\)", source))
    assert used <= english_keys(), used - english_keys()


@pytest.mark.parametrize("name", ["app.js", "translations.js"])
def test_js_files_do_not_use_innerhtml(name):
    source = (STATIC / "js" / name).read_text(encoding="utf-8")
    assert "innerHTML" not in source and "outerHTML" not in source
    assert "insertAdjacentHTML" not in source and "document.write" not in source


def test_translation_languages_match_guide_service():
    from app.services.guides import LANG_NAMES

    source = (STATIC / "js" / "translations.js").read_text(encoding="utf-8")
    codes = set(
        re.findall(r"^  ([a-z]{2}): \{", source[: source.index("const GUIDE_LABELS")], re.M)
    )
    assert codes == set(LANG_NAMES)


def test_manifest_is_valid_json():
    json.loads((STATIC / "manifest.json").read_text(encoding="utf-8"))
