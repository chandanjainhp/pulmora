# Pulmora 



## What's inside

```
app/
  main.py            FastAPI app: CORS, routers, /health, lifespan model load
  core/config.py     Settings (pydantic-settings) with .env support
  core/security.py   bcrypt hashing, JWT create/decode, auth dependency
  core/rate_limit.py slowapi limiter (applied to POST /predict)
  db/session.py      engine, SessionLocal, Base, get_db dependency
  models/            SQLAlchemy ORM models (user, prediction)
  schemas/           Pydantic v2 request/response models
  services/
    ml_service.py    trains the LogisticRegression once at startup
    premium.py       insurance premium calculation (ported verbatim)
    doctors.py       doctor recommendation logic (ported verbatim)
    pipeline.py      orchestration: predict -> premium -> doctor -> persist
    pdf_report.py    WeasyPrint PDF generation from insurance_report.html
  routers/
    auth.py          POST /auth/register, POST /auth/login, GET /auth/me
    predict.py       POST /predict (rate-limited)
    reports.py       GET /reports, GET /reports/{id} (PDF)
    pages.py         HTML pages under /pages/* (original templates)
templates/           the original Django templates (Jinja2-adapted)
static/              the original static assets (css/js/images/dataset)
alembic/             migrations (initial schema included)
scripts/             import_sqlite_data.py (Django db.sqlite3 -> new schema)
tests/               pytest + httpx AsyncClient suite
```

## Requirements

* Python 3.12+
* For PDF generation, WeasyPrint needs system libraries
  (`libpango`, `libcairo`, …): on Debian/Ubuntu
  `sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0`,
  on macOS `brew install pango`. (Everything else is pure pip.)

## Setup

```bash
cd lung-cancer-fastapi

# 1. virtual environment
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. dependencies
pip install -r requirements.txt

# 3. configuration (optional - sane dev defaults are built in)
cp .env.example .env                  # then edit SECRET_KEY at minimum

# 4. database (SQLite by default; DATABASE_URL is configurable)
alembic upgrade head

# 5. (optional) import users from the original Django project
python scripts/import_sqlite_data.py \
    --source ../LungCancerPrediction-full-developer/db.sqlite3

# 6. run
uvicorn app.main:app --reload
```

Then open:

| URL | What |
| --- | --- |
| http://127.0.0.1:8000/ | redirects to the home page |
| http://127.0.0.1:8000/pages/home | landing page (original template) |
| http://127.0.0.1:8000/pages/signin | browser sign-in |
| http://127.0.0.1:8000/docs | interactive OpenAPI docs |
| http://127.0.0.1:8000/health | liveness probe |

## API summary

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/register` | – | Create account (JSON) |
| POST | `/auth/login` | – | OAuth2 password form → `{access_token}` |
| GET | `/auth/me` | JWT | Current user |
| POST | `/predict` | JWT | 22 features → risk class, probability, premium, doctors (rate-limited) |
| GET | `/reports` | JWT | List your stored reports |
| GET | `/reports/{prediction_id}` | JWT | PDF report (`application/pdf`) |
| GET | `/health` | – | Liveness |
| GET/POST | `/pages/*` | cookie | Original HTML UI |

### Quick API example

```bash
# register
curl -X POST http://127.0.0.1:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"first_name":"Jane","last_name":"Doe","username":"jane","email":"jane@example.com",
       "password":"secret123","confirm_password":"secret123"}'

# login (form-encoded)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -d 'username=jane&password=secret123' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# predict
curl -X POST http://127.0.0.1:8000/predict \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"age":55,"gender":1,"air_pollution":7,"alcohol_use":8,"dust_allergy":7,
       "occupational_hazards":6,"genetic_risk":7,"chronic_lung_disease":6,
       "balanced_diet":6,"obesity":7,"smoking":8,"passive_smoker":7,
       "chest_pain":8,"coughing_of_blood":8,"fatigue":8,"weight_loss":7,
       "shortness_of_breath":8,"wheezing":8,"swallowing_difficulty":7,
       "clubbing_of_finger_nails":8,"frequent_cold":6,"dry_cough":7,"snoring":7}'

# PDF report (use the id returned above)
curl -OJ -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/reports/1
```

## Configuration

All settings live in `app/core/config.py` and can be overridden via
environment variables or `.env` (see `.env.example`): `DATABASE_URL`
(default `sqlite:///./db.sqlite3`, any SQLAlchemy URL works), `SECRET_KEY`,
`ACCESS_TOKEN_EXPIRE_MINUTES`, `DATASET_PATH`, `PREDICT_RATE_LIMIT`
(slowapi syntax, default `10/minute`), `CORS_ORIGINS`, `INR_CONVERSION_RATE`.

## Security notes (read MIGRATION_NOTES.md for the full picture)

* **Auth**: JWT (HS256) via `python-jose`; passwords bcrypt-hashed with
  passlib. The browser pages use the same JWT in an `HttpOnly` +
  `SameSite=Strict` cookie.
* **CSRF-equivalent protection**: Django's per-form CSRF tokens are gone
  because the API is token/header-authenticated. For the cookie-based HTML
  flow, `SameSite=Strict` prevents cross-site form posts; additionally the
  app only mutates state on `POST` endpoints that require the JWT cookie,
  and JSON API calls require the `Authorization` header (which cross-site
  forms cannot set). If you serve the UI from another origin, keep CORS
  origins explicit in `CORS_ORIGINS`.
* **Rate limiting**: `POST /predict` is limited to 10 requests/minute per IP
  (configurable via `PREDICT_RATE_LIMIT`).
* **Validation**: all 22 inputs are validated server-side (age ≥ 1,
  gender ∈ {1, 2}, symptom scales 1–8), matching the original HTML form.
* **Report access**: `/reports/{id}` returns 404 (not 403) for other users'
  reports so ids cannot be enumerated.

## Tests

```bash
pytest
```

56 tests cover every endpoint (auth, predict, reports, pages, health),
premium/doctor business-rule parity against the original code's outputs,
input validation, rate limiting, and the Django user import.

## Model

A `LogisticRegression` is trained at startup (FastAPI lifespan) on
`static/dataset/lungcancer.csv` — same split (`test_size=0.25`,
`random_state=1`) and same features as the original `views.py`, so
predictions match the Django app. The original retrained on every request;
this version trains once and holds the model in memory.
