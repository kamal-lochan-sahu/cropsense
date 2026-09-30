import app as app_package


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"CropSense" in response.data


def test_health(client):
    body = client.get("/health").get_json()
    assert body == {"status": "ok", "model_loaded": True, "guides_configured": True}


def test_security_headers(client):
    headers = client.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in headers


def test_unknown_route_is_plain_404(client):
    assert client.get("/nope").status_code == 404


def test_gunicorn_style_lookup_builds_app_lazily():
    # `gunicorn app:app` resolves the attribute `app` on the package.
    instance = app_package.app
    assert instance.name == "app"
