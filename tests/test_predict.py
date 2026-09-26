"""Tests for POST /predict (JSON API)."""
import pytest

from tests.conftest import VALID_PREDICTION, register_and_login, unique

from app.db.session import SessionLocal
from app.models.prediction import Prediction
from app.services.premium import build_risk_factors, calculate_premium


async def test_predict_requires_auth(client):
    response = await client.post("/predict", json=VALID_PREDICTION)
    assert response.status_code == 401


async def test_predict_success(client):
    headers = await register_and_login(client)
    response = await client.post("/predict", json=VALID_PREDICTION, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["diagnosis"] in ("Positive", "Medium", "Negative")
    assert body["diagnosis_code"] in (1, 0, -1)
    assert 0.0 <= body["probability"] <= 1.0
    # 11 risk factors, exact names/order as the original view
    assert [f["name"] for f in body["risk_factors"]][0] == "Age"
    assert len(body["risk_factors"]) == 11
    # Doctor recommendation consistent with the diagnosis
    expected_doctor = {
        "Positive": "Dr. Michael Chen",
        "Medium": "Dr. Sarah Johnson",
        "Negative": "Dr. Emily Rodriguez",
    }[body["diagnosis"]]
    assert body["doctor"]["name"] == expected_doctor
    # Digital signature format from views.py
    assert body["digital_signature"].startswith(
        "Verified by Pulmora on "
    )
    assert body["report_date"]

    # Premium parity: the API premium must equal what the original
    # calculate_premium produces for the same inputs + returned diagnosis.
    rf = build_risk_factors(
        body["risk_factors"][0]["value"],  # age
        VALID_PREDICTION["air_pollution"],
        VALID_PREDICTION["alcohol_use"],
        VALID_PREDICTION["dust_allergy"],
        VALID_PREDICTION["occupational_hazards"],
        VALID_PREDICTION["genetic_risk"],
        VALID_PREDICTION["chronic_lung_disease"],
        VALID_PREDICTION["smoking"],
        VALID_PREDICTION["passive_smoker"],
        VALID_PREDICTION["chest_pain"],
        VALID_PREDICTION["coughing_of_blood"],
    )
    expected_amount, expected_factors = calculate_premium(
        VALID_PREDICTION["age"], VALID_PREDICTION["gender"],
        body["diagnosis"], rf,
    )
    assert body["premium_amount"] == expected_amount
    assert body["premium_factors"] == expected_factors


async def test_predict_persists_to_database(client):
    headers = await register_and_login(client)
    response = await client.post("/predict", json=VALID_PREDICTION, headers=headers)
    prediction_id = response.json()["id"]

    db = SessionLocal()
    try:
        row = db.get(Prediction, prediction_id)
        assert row is not None
        assert row.diagnosis in ("Positive", "Medium", "Negative")
        assert row.age == VALID_PREDICTION["age"]
        assert row.snoring == VALID_PREDICTION["snoring"]
        assert len(row.risk_factors) == 11
        assert row.doctor["name"]
    finally:
        db.close()


async def test_prediction_is_deterministic(client):
    """Same input -> same diagnosis (the model is loaded once and reused)."""
    headers = await register_and_login(client)
    first = (await client.post("/predict", json=VALID_PREDICTION, headers=headers)).json()
    second = (await client.post("/predict", json=VALID_PREDICTION, headers=headers)).json()
    assert first["diagnosis"] == second["diagnosis"]
    assert first["diagnosis_code"] == second["diagnosis_code"]


@pytest.mark.parametrize(
    "override",
    [
        {"age": 0},          # below form minimum (min="1")
        {"age": -5},
        {"gender": 3},       # form only offers 1 / 2
        {"gender": 0},
        {"air_pollution": 0},   # below range min
        {"air_pollution": 9},   # above range max
        {"smoking": 10},
        {"snoring": -1},
    ],
)
async def test_predict_rejects_out_of_range_input(client, override):
    headers = await register_and_login(client)
    payload = {**VALID_PREDICTION, **override}
    response = await client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 422, (override, response.text)


async def test_predict_missing_field(client):
    headers = await register_and_login(client)
    payload = dict(VALID_PREDICTION)
    del payload["wheezing"]
    response = await client.post("/predict", json=payload, headers=headers)
    assert response.status_code == 422
