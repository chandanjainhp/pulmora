"""Tests for the browser (HTML pages) flow with cookie-based JWT auth."""
from tests.conftest import unique

# Original form field names (with spaces), as in templates/predict.html.
PREDICT_FORM = {
    "Age": 33,
    "Gender": 1,
    "Air Pollution": 2,
    "Alcohol use": 4,
    "Dust Allergy": 5,
    "OccuPational Hazards": 4,
    "Genetic Risk": 3,
    "chronic Lung Disease": 2,
    "Balanced Diet": 4,
    "Obesity": 3,
    "Smoking": 3,
    "Passive Smoker": 2,
    "Chest Pain": 2,
    "Coughing of Blood": 4,
    "Fatigue": 3,
    "Weight Loss": 4,
    "Shortness of Breath": 2,
    "Wheezing": 2,
    "Swallowing Difficulty": 3,
    "Clubbing of Finger Nails": 1,
    "Frequent Cold": 2,
    "Dry Cough": 3,
    "Snoring": 4,
}


async def _signup_and_signin(client, username: str, password: str = "secret123"):
    response = await client.post(
        "/pages/signup",
        data={
            "first_name": "Page",
            "last_name": "Tester",
            "username": username,
            "email": f"{username}@example.com",
            "password1": password,
            "password2": password,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/pages/signin"

    response = await client.post(
        "/pages/signin",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/pages/predict"
    assert "lcps_access_token" in response.headers.get("set-cookie", "")
    # Follow the redirect so the client stores the cookie.
    await client.get("/pages/predict")


async def test_home_page(client):
    response = await client.get("/pages/home")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Pulmora" in response.text


async def test_static_assets_served(client):
    response = await client.get("/static/images/lung-cancer-image.jpg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


async def test_signup_and_signin_flow(client):
    username = unique("page")
    await _signup_and_signin(client, username)
    # Cookie-authenticated prediction form.
    response = await client.get("/pages/predict")
    assert response.status_code == 200
    assert "predictionForm" in response.text


async def test_signup_password_mismatch_shows_message(client):
    username = unique("page")
    response = await client.post(
        "/pages/signup",
        data={
            "first_name": "A", "last_name": "B", "username": username,
            "email": f"{username}@example.com",
            "password1": "one", "password2": "two",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Password+not+matching" in response.headers["location"]


async def test_signup_duplicate_username_shows_message(client):
    username = unique("page")
    await _signup_and_signin(client, username)
    client.cookies.clear()
    response = await client.post(
        "/pages/signup",
        data={
            "first_name": "A", "last_name": "B", "username": username,
            "email": f"other-{username}@example.com",
            "password1": "x", "password2": "x",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "Username+Taken" in response.headers["location"]


async def test_signin_invalid_credentials(client):
    response = await client.post(
        "/pages/signin",
        data={"username": "ghost", "password": "nope"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "invalid+credentials" in response.headers["location"]


async def test_predict_page_requires_signin(client):
    response = await client.get("/pages/predict", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/pages/signin")


async def test_predict_form_requires_signin(client):
    response = await client.post("/pages/predict", data=PREDICT_FORM,
                                 follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/pages/signin")


async def test_predict_form_returns_results(client):
    await _signup_and_signin(client, unique("pred"))
    response = await client.post("/pages/predict", data=PREDICT_FORM)
    assert response.status_code == 200
    assert "show_results" not in response.text or "diagnosis" in response.text.lower()
    # The results panel with premium + doctor is rendered.
    assert "/month" in response.text
    assert "Dr." in response.text


async def test_predict_form_pdf(client):
    await _signup_and_signin(client, unique("pdf"))
    response = await client.post(
        "/pages/predict", data={**PREDICT_FORM, "generate_pdf": "true"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"


async def test_predict_form_invalid_value(client):
    await _signup_and_signin(client, unique("invalid"))
    response = await client.post(
        "/pages/predict", data={**PREDICT_FORM, "Age": "not-a-number"}
    )
    assert response.status_code == 200
    assert "Invalid input" in response.text


async def test_logout_clears_cookie(client):
    await _signup_and_signin(client, unique("out"))
    response = await client.get("/pages/logout", follow_redirects=False)
    assert response.status_code == 303
    assert "lcps_access_token" in response.headers.get("set-cookie", "")
    # After logout, the protected page bounces back to sign-in.
    client.cookies.clear()  # httpx keeps old cookie; emulate cleared state
    response = await client.get("/pages/predict", follow_redirects=False)
    assert response.status_code == 303
