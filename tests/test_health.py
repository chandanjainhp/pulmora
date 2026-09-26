"""Liveness probe and app startup."""


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True


async def test_root_redirects_to_pages_home(client):
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (307, 302, 303, 307)
    assert response.headers["location"].endswith("/pages/home")


async def test_interactive_docs_available(client):
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/redoc")).status_code == 200
    openapi = (await client.get("/openapi.json")).json()
    paths = openapi["paths"]
    for path in (
        "/auth/register",
        "/auth/login",
        "/auth/me",
        "/predict",
        "/reports/{prediction_id}",
        "/health",
    ):
        assert path in paths, path
