#!/usr/bin/env python3
"""One-off migration script: copy users from the legacy Django db.sqlite3
into the new FastAPI schema.

Usage (from the lung-cancer-fastapi project root, after
``alembic upgrade head``):

    python scripts/import_sqlite_data.py --source ../LungCancerPrediction-full-developer/db.sqlite3

What it does
------------
* Reads ``auth_user`` rows from the Django database.
* Inserts them into the new ``users`` table with
  ``legacy_password_hash`` set to the original Django ``pbkdf2_sha256$...``
  hash and ``hashed_password`` set to an unusable bcrypt placeholder.
* On the first successful sign-in, the app verifies the Django hash and
  transparently upgrades it to bcrypt (see app/core/security.py).
* Skips users whose username/email already exist (safe to re-run).
* The Django app had no prediction model (Home/models.py was empty), so
  there is no prediction data to copy.

Nothing is deleted from the source database - the script only reads it.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `app` importable when running from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from passlib.context import CryptContext  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402

# Unusable placeholder bcrypt hash (passlib "!" scheme marker is not bcrypt;
# we use a random bcrypt digest that no password can verify against, and the
# legacy hash is always tried first for imported users).
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
UNUSABLE_HASH = _pwd.hash("__imported_from_django__unset__")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--source",
        default="../LungCancerPrediction-full-developer/db.sqlite3",
        help="Path to the legacy Django db.sqlite3 (read-only)",
    )
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"[skip] Source database not found: {source}")
        print("       (the original project shipped without a db.sqlite3 file;")
        print("        run this on the machine that has your production data)")
        return 0

    conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, username, email, first_name, last_name, password,
                   is_active, is_superuser, date_joined, last_login
            FROM auth_user
            ORDER BY id
            """
        ).fetchall()
    except sqlite3.OperationalError as exc:
        print(f"[error] Could not read auth_user from {source}: {exc}")
        return 1
    finally:
        conn.close()

    if not rows:
        print("[ok] No users found in the source database - nothing to import.")
        return 0

    db = SessionLocal()
    imported = skipped = 0
    try:
        for row in rows:
            exists = db.scalar(select(User).where(User.username == row["username"]))
            if exists is not None:
                print(f"  [skip] username={row['username']!r} already exists")
                skipped += 1
                continue
            if row["email"] and db.scalar(
                select(User).where(User.email == row["email"])
            ):
                print(f"  [skip] email={row['email']!r} already exists")
                skipped += 1
                continue

            user = User(
                username=row["username"],
                email=row["email"] or f"{row['username']}@invalid.local",
                first_name=row["first_name"] or "",
                last_name=row["last_name"] or "",
                hashed_password=UNUSABLE_HASH,
                # Keep the Django hash until the user logs in once.
                legacy_password_hash=row["password"],
                is_active=bool(row["is_active"]),
                is_superuser=bool(row["is_superuser"]),
                created_at=datetime.fromisoformat(row["date_joined"])
                if row["date_joined"]
                else datetime.now(timezone.utc),
                last_login=datetime.fromisoformat(row["last_login"])
                if row["last_login"]
                else None,
            )
            db.add(user)
            try:
                db.commit()
                imported += 1
                print(f"  [ok]   username={row['username']!r} imported")
            except IntegrityError:
                db.rollback()
                print(f"  [skip] username={row['username']!r} (integrity error)")
                skipped += 1
    finally:
        db.close()

    print(
        f"\nDone: {imported} user(s) imported, {skipped} skipped. "
        "Imported users log in with their existing Django password "
        "(it is upgraded to bcrypt on first login)."
    )
    print(
        "Note: the Django app stored no predictions "
        "(Home/models.py had no models), so nothing else to copy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
