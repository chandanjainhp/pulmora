"""Shared test fixtures.

Environment is configured BEFORE the app is imported, so every test uses a
throwaway SQLite database and a permissive rate limit (a dedicated test below
exercises the actual rate limiter by patching the settings object).
"""
from __future__ import annotations

import os
import tempfile
import uuid

TEST_DB_DIR = tempfile.mkdtemp(prefix="lcps_test_")
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.db")

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["PREDICT_RATE_LIMIT"] = "1000/minute"

# Import after the env vars above are in place.
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app import models  # noqa: E402,F401  (register tables)
from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.services.ml_service import train_model  # noqa: E402

# Train once for the whole test session (the lifespan handler normally does
# this at startup; ASGITransport does not run lifespan automatically).
app.state.ml_model = train_model(settings.DATASET_PATH)

Base.metadata.create_all(engine)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


@pytest.fixture
async def client():
    """Async HTTP client wired to the app (does not follow redirects)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


async def register_and_login(
    client: AsyncClient, username: str | None = None, password: str = "secret123"
) -> dict:
    """Register a user and return Authorization headers with a JWT."""
    username = username or unique("user")
    response = await client.post(
        "/auth/register",
        json={
            "first_name": "Test",
            "last_name": "User",
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "confirm_password": password,
        },
    )
    assert response.status_code == 201, response.text
    response = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


VALID_PREDICTION = {
    "age": 55,
    "gender": 1,
    "air_pollution": 7,
    "alcohol_use": 8,
    "dust_allergy": 7,
    "occupational_hazards": 6,
    "genetic_risk": 7,
    "chronic_lung_disease": 6,
    "balanced_diet": 6,
    "obesity": 7,
    "smoking": 8,
    "passive_smoker": 7,
    "chest_pain": 8,
    "coughing_of_blood": 8,
    "fatigue": 8,
    "weight_loss": 7,
    "shortness_of_breath": 8,
    "wheezing": 8,
    "swallowing_difficulty": 7,
    "clubbing_of_finger_nails": 8,
    "frequent_cold": 6,
    "dry_cough": 7,
    "snoring": 7,
}
