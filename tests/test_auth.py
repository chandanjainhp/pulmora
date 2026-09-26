from tests.conftest import unique


async def test_register_success(client):
    username = unique("reg")
    response = await client.post(
        "/auth/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == username
    assert body["first_name"] == "Jane"
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_username(client):
    username = unique("dup")
    payload = {
        "first_name": "A",
        "last_name": "B",
        "username": username,
        "email": f"{username}@example.com",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    payload["email"] = f"other-{username}@example.com"
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Username Taken"


async def test_register_duplicate_email(client):
    username = unique("dup")
    payload = {
        "first_name": "A",
        "last_name": "B",
        "username": username,
        "email": f"{username}@example.com",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    payload["username"] = unique("dup2")
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


async def test_register_password_mismatch(client):
    username = unique("mismatch")
    response = await client.post(
        "/auth/register",
        json={
            "first_name": "A",
            "last_name": "B",
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret123",
            "confirm_password": "different",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Password not matching.."


async def test_register_invalid_email(client):
    response = await client.post(
        "/auth/register",
        json={
            "first_name": "A",
            "last_name": "B",
            "username": unique("badmail"),
            "email": "not-an-email",
            "password": "secret123",
            "confirm_password": "secret123",
        },
    )
    assert response.status_code == 422


async def test_login_returns_token(client):
    from tests.conftest import register_and_login

    headers = await register_and_login(client)
    assert headers["Authorization"].startswith("Bearer ")


async def test_login_wrong_password(client):
    from tests.conftest import register_and_login

    username = unique("wrongpw")
    await register_and_login(client, username=username, password="correct-horse")
    response = await client.post(
        "/auth/login", data={"username": username, "password": "wrong"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


async def test_login_unknown_user(client):
    response = await client.post(
        "/auth/login", data={"username": "no-such-user-xyz", "password": "x"}
    )
    assert response.status_code == 401


async def test_me_requires_auth(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_with_bad_token(client):
    response = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


async def test_me_success(client):
    from tests.conftest import register_and_login

    username = unique("me")
    headers = await register_and_login(client, username=username)
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == username
    assert body["email"] == f"{username}@example.com"
    assert body["is_active"] is True
