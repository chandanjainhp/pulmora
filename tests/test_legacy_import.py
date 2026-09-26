"""Legacy Django user import: pbkdf2 verification, transparent upgrade to
bcrypt, and the scripts/import_sqlite_data.py one-off migration."""
import base64
import hashlib
import sqlite3

from app.core.security import _verify_django_pbkdf2_sha256, verify_password
from app.db.session import SessionLocal
from app.models.user import User
from tests.conftest import unique


def _django_hash(password: str, iterations: int = 600000, salt: str = "somesalt") -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${base64.b64encode(digest).decode()}"


def test_verify_django_pbkdf2_sha256():
    encoded = _django_hash("correct battery horse staple")
    assert _verify_django_pbkdf2_sha256("correct battery horse staple", encoded)
    assert not _verify_django_pbkdf2_sha256("wrong password", encoded)
    assert not _verify_django_pbkdf2_sha256("x", "not-a-django-hash")
    assert not _verify_django_pbkdf2_sha256("x", "md5$1$salt$hash")


def test_verify_password_falls_back_to_legacy_hash():
    legacy = _django_hash("old-django-password")
    assert verify_password("old-django-password", None, legacy)
    assert not verify_password("wrong", None, legacy)


def _make_legacy_django_db(path: str, username: str, password: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE auth_user (
            id INTEGER PRIMARY KEY,
            password TEXT NOT NULL,
            last_login TEXT,
            is_superuser INTEGER NOT NULL,
            username TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            is_staff INTEGER NOT NULL,
            is_active INTEGER NOT NULL,
            date_joined TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO auth_user (password, last_login, is_superuser, username,"
        " first_name, last_name, email, is_staff, is_active, date_joined)"
        " VALUES (?, NULL, 0, ?, ?, ?, ?, 0, 1, ?)",
        (
            _django_hash(password),
            username,
            "Leg",
            "Acy",
            f"{username}@example.com",
            "2024-01-15 10:30:00",
        ),
    )
    conn.commit()
    conn.close()


async def test_import_script_imports_users_and_login_upgrades_hash(client, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    username = unique("legacy")
    source_db = tmp_path / "db.sqlite3"
    _make_legacy_django_db(str(source_db), username, "django-secret-pw")

    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "import_sqlite_data.py"),
            "--source",
            str(source_db),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "imported" in result.stdout

    # The user exists in the new schema with the legacy hash attached.
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).one()
        assert user.legacy_password_hash is not None
        assert user.legacy_password_hash.startswith("pbkdf2_sha256$")
    finally:
        db.close()

    # Login with the ORIGINAL Django password works and upgrades to bcrypt.
    response = await client.post(
        "/auth/login", data={"username": username, "password": "django-secret-pw"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    db = SessionLocal()
    try:
        db.expire_all()
        user = db.query(User).filter(User.username == username).one()
        assert user.legacy_password_hash is None
        assert user.hashed_password.startswith("$2")  # bcrypt
        assert user.last_login is not None
    finally:
        db.close()

    # /auth/me works with the issued token.
    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == username

    # Re-running the script skips the already-imported user (idempotent).
    result2 = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "import_sqlite_data.py"),
            "--source",
            str(source_db),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result2.returncode == 0
    assert "already exists" in result2.stdout


async def test_import_script_missing_source(client, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "import_sqlite_data.py"),
            "--source",
            str(tmp_path / "does-not-exist.sqlite3"),
        ],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    assert result.returncode == 0
    assert "not found" in result.stdout
