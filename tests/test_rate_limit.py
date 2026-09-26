"""Rate limiting on POST /predict (slowapi)."""

from app.core.config import settings


async def test_predict_rate_limited(client, monkeypatch):
    # The limit is read from settings at request time, so patch it here.
    monkeypatch.setattr(settings, "PREDICT_RATE_LIMIT", "2/minute")

    from tests.conftest import VALID_PREDICTION, register_and_login

    headers = await register_and_login(client)
    first = await client.post("/predict", json=VALID_PREDICTION, headers=headers)
    second = await client.post("/predict", json=VALID_PREDICTION, headers=headers)
    third = await client.post("/predict", json=VALID_PREDICTION, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
