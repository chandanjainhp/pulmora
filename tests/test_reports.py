"""Tests for /reports (PDF download + listing)."""
from tests.conftest import VALID_PREDICTION, register_and_login, unique


async def _create_prediction(client, headers) -> int:
    response = await client.post(
        "/predict", json=VALID_PREDICTION, headers=headers
    )
    assert response.status_code == 200
    return response.json()["id"]


async def test_report_requires_auth(client):
    response = await client.get("/reports/1")
    assert response.status_code == 401


async def test_report_returns_pdf(client):
    headers = await register_and_login(client)
    prediction_id = await _create_prediction(client, headers)

    response = await client.get(f"/reports/{prediction_id}", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"
    assert "Lung_Cancer_Insurance_Report_" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].startswith("inline")


async def test_report_unknown_id_is_404(client):
    headers = await register_and_login(client)
    response = await client.get("/reports/999999", headers=headers)
    assert response.status_code == 404


async def test_report_not_visible_to_other_users(client):
    headers_a = await register_and_login(client)
    prediction_id = await _create_prediction(client, headers_a)

    headers_b = await register_and_login(client)
    response = await client.get(f"/reports/{prediction_id}", headers=headers_b)
    assert response.status_code == 404  # 404, not 403: ids are not enumerable


async def test_report_listing(client):
    headers = await register_and_login(client)
    first = await _create_prediction(client, headers)
    second = await _create_prediction(client, headers)

    response = await client.get("/reports", headers=headers)
    assert response.status_code == 200
    body = response.json()
    ids = {r["id"] for r in body["reports"]}
    assert {first, second} <= ids
    for report in body["reports"]:
        assert report["diagnosis"] in ("Positive", "Medium", "Negative")
        assert report["pdf_url"].startswith("/reports/")
