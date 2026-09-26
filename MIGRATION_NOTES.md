# Migration Notes: Django → FastAPI

Everything the original "Lung Cancer Prediction System" did, where it now
lives, and every deliberate change. The original Django project is kept
untouched next to this folder (`../LungCancerPrediction-full-developer`) so
you can diff file by file.

## 1. File mapping

| Original (Django) | New (FastAPI) | Notes |
| --- | --- | --- |
| `manage.py` | `uvicorn app.main:app --reload` | no management command wrapper needed |
| `LungCancerPrediction/settings.py` | `app/core/config.py` | pydantic-settings; DB URL, secret key etc. via env/.env |
| `LungCancerPrediction/urls.py` | `app/main.py` | router wiring, static mount, CORS, lifespan |
| `Home/views.py::home` | `app/routers/pages.py::home` | GET /pages/home (also `/` redirects there) |
| `Home/views.py::signup` | `app/routers/pages.py::signup*` + `app/routers/auth.py::register` | browser form + JSON API |
| `Home/views.py::signin` | `app/routers/pages.py::signin*` + `app/routers/auth.py::login` | cookie flow + OAuth2 token flow |
| `Home/views.py::logout` | `app/routers/pages.py::logout` | **note:** the original view existed but had no URL wired in `Home/urls.py` (dead code); it is now reachable at `/pages/logout` |
| `Home/views.py::predict` | `app/routers/predict.py` + `app/routers/pages.py::predict_submit` + `app/services/pipeline.py` | logic split into model/premium/doctor services |
| `Home/views.py::render_to_pdf` (xhtml2pdf, PyPDF2) | `app/services/pdf_report.py` (WeasyPrint) | same template, same filename scheme |
| `Home/views.py::calculate_premium` | `app/services/premium.py::calculate_premium` | verbatim port (see §3) |
| `Home/views.py::get_doctor_recommendation` | `app/services/doctors.py` | verbatim port |
| `Home/views.py` model training block | `app/services/ml_service.py::train_model` | trained once in lifespan, not per request |
| `Home/models.py` | `app/models/prediction.py` | original was empty — no models existed |
| (django.contrib.auth User) | `app/models/user.py` | see §4 |
| `Home/admin.py` | — | nothing was registered; dropped (FastAPI has no admin; use /docs or a future admin UI) |
| `Home/urls.py` | router prefixes in `app/routers/*` | see §2 |
| `templates/*.html` | `templates/*.html` (adapted, see §5) | same look & feel |
| `static/**` | `static/**` (copied) | served at the same `/static/` URLs |
| `static/dataset/lungcancer.csv` | `static/dataset/lungcancer.csv` | training data (path configurable via `DATASET_PATH`) |
| `files/` (collectstatic output) | — | build artifact, not needed |
| `view_db.py` | — | debugging utility, not migrated |
| `db.sqlite3` (not in the zip) | new `db.sqlite3` via Alembic | users copied by `scripts/import_sqlite_data.py` |

New files with no Django counterpart: `app/core/security.py`,
`app/core/rate_limit.py`, `app/db/session.py`, `app/schemas/*`,
`app/services/pipeline.py`, `alembic/*`, `scripts/import_sqlite_data.py`,
`tests/*`.

## 2. URL mapping

| Django URL | FastAPI URL |
| --- | --- |
| `/` , `/home` | `/pages/home` (and `/` redirects to it) |
| `/signup` (GET/POST) | `/pages/signup` (GET/POST), JSON: `POST /auth/register` |
| `/signin` (GET/POST) | `/pages/signin` (GET/POST), JSON: `POST /auth/login` |
| `/predict` (GET/POST) | `/pages/predict` (GET/POST), JSON: `POST /predict` |
| (none; dead code) | `/pages/logout` |
| (none) | `GET /auth/me`, `GET /reports`, `GET /reports/{id}`, `GET /health` |
| (admin) | not migrated (was unused) |

## 3. Business rules — preserved exactly

All thresholds, formulas and mappings were ported verbatim and are pinned by
tests (`tests/test_premium_doctors.py`) against golden outputs computed by
running the **original** `Home/views.py` code:

* diagnosis mapping: `1 → Positive`, `0 → Medium`, else `Negative`;
* the 11 risk factors and their High/Medium/Low thresholds
  (age > 60 / > 40; symptom > 6 / > 3);
* `calculate_premium`: base 50 USD, age factor `age/10`, gender factor
  1.1 (male), diagnosis factors 3.0 / 1.5 / 1.0, per-factor impacts
  (Age ×5, Smoking >4 ×3, Genetic Risk >4 ×2.5, chronic Lung Disease >4
  ×2.8, others >5 ×1.2), ×75 INR conversion, rounding to 2 decimals;
* doctor mapping: Positive → Dr. Michael Chen, Medium → Dr. Sarah Johnson,
  Negative (and anything else) → Dr. Emily Rodriguez;
* digital signature text: `Verified by LC Cancer Prediction System on
  YYYY-MM-DD HH:MM:SS`;
* PDF filename: `Lung_Cancer_Insurance_Report_{username}_{YYYYMMDD}.pdf`
  served `inline`;
* model: `LogisticRegression()` with default hyperparameters, features =
  the first 23 CSV columns, `train_test_split(test_size=0.25,
  random_state=1)` — including fitting on the *training split only*, as the
  original did.

### ⚠ Flagged: known bug kept for price parity

The original `calculate_premium` loop ends with

```python
risk_premium += impact if 'impact' in locals() else 0
```

`impact` is never reset between iterations, so **any factor that matches no
branch silently re-uses the previous factor's impact**. Example from the
original code: a 33-year-old with low values gets `Age Factor` counted 11
times (₹19,098.75 instead of ₹5,486.25). This behaviour is **preserved
bug-for-bug** in `app/services/premium.py` and pinned by the golden-vector
tests, because "fixing" it would change every quoted premium. If you want the
correct behaviour, reset `impact` at the top of each loop iteration — but be
aware this changes premiums, tests, and historical comparisons.

Other small original quirks handled deliberately:

* **Signup "email exists" branch** in Django showed the message but then
  fell through to `return redirect('/')` (no redirect back to signup). The
  new code redirects back to `/pages/signup?msg=Email+already+exists`,
  which matches the message but fixes the fall-through.
* **LogisticRegression convergence warning**: the original training emits a
  `ConvergenceWarning` (max_iter=100). Kept identical — we do not raise
  `max_iter` because it could change prediction boundaries slightly.
* **Prediction probability** is new: the original returned only the class.
  We report `predict_proba` of the predicted class. Class labels and the
  training procedure are unchanged, so classes match the Django app on the
  same scikit-learn version.

## 4. Deliberate deviations (flagged, not silently changed)

1. **`POST /predict` now requires authentication.** The original Django view
   let anonymous visitors run predictions (results lived only in the
   session). Predictions are now persisted per user, so a JWT is required.
   If you need anonymous predictions, remove the `get_current_user`
   dependency — the pipeline itself does not need a user.
2. **Input validation is enforced server-side** (age ≥ 1, gender ∈ {1, 2},
   symptom scales 1–8), mirroring the original HTML form's `min`/`max`.
   Note the *dataset* contains some 9s for a few symptoms, but the original
   UI could never submit them, so they are rejected (documented in
   `app/schemas/prediction.py`). The original Django view accepted any
   integer and would crash on non-numeric input; the new form re-renders
   with an "Invalid input" message instead of a 500.
3. **Predictions are stored** (new `predictions` table) so PDFs can be
   regenerated later via `GET /reports/{id}`. In Django, results lived only
   in the request session.
4. **Auth**: session cookies → JWT (`python-jose`, HS256, 24 h) with
   bcrypt-hashed passwords (`passlib`). Django's `auth_user` rows can be
   imported with `scripts/import_sqlite_data.py`; imported users keep their
   Django `pbkdf2_sha256` hash, log in with their old password, and are
   upgraded to bcrypt transparently on first login.
   `is_staff` was dropped (never used); `is_superuser`, `is_active`,
   `date_joined` (→ `created_at`) and `last_login` are preserved.
5. **CSRF**: Django's per-form CSRF tokens are replaced by (a) header-based
   Bearer auth for the JSON API — cross-site forms cannot attach headers —
   and (b) an `HttpOnly`, `SameSite=Strict` cookie for the HTML pages, which
   stops cross-site POSTs from browsers. No secret is exposed to JS. See
   README "Security notes".
6. **Rate limiting** (`slowapi`) on `POST /predict`: 10/minute per IP by
   default (`PREDICT_RATE_LIMIT`).
7. **PDF engine**: xhtml2pdf/PyPDF2 → WeasyPrint, rendering the *same*
   `insurance_report.html` template with the same context keys.
8. **Message flashes** (Django `messages`) → query parameter `?msg=…`
   rendered by the same `{% for message in messages %}` blocks in the
   templates.

## 5. Template changes (kept minimal)

| Change | Why |
| --- | --- |
| `{% load static %}` lines removed | Jinja2 has no template-tag loading |
| `{% static 'x' %}` → `{{ static('x') }}` | Jinja2 function global, resolves to `/static/x` |
| `{% csrf_token %}` removed | JWT auth (see §4.3); forms post to the same relative actions as before |
| `{% now "Y" %}` → `{{ now_year }}` | Jinja2 has no `{% now %}` tag; passed in context |
| `predict.html`: added a small `<mess>` messages block | the original predict page had no way to show errors; reuses the exact markup used by signin.html/signup.html |

No CSS/JS/layout was modified — the pages are byte-identical apart from the
tag substitutions above, so the responsive/mobile styling is unchanged.

## 6. Dropped (unused or obsolete)

* `Home/admin.py` — empty; Django admin not migrated.
* `files/` — collectstatic output directory (build artifact).
* `view_db.py` — ad-hoc database inspection script.
* `static/plugins/font-awesome-4.7.0` etc. — kept as-is in `static/`, they
  are still referenced by the templates.
* PyPDF2 import in the original `views.py` — it was imported but never
  used (the original only ever wrote PDFs via xhtml2pdf).

## 7. Running the old and new side by side

The Django project (`python manage.py runserver`, port 8000) and the
FastAPI app (`uvicorn app.main:app --reload`, also port 8000) cannot share a
port — run the new one on another port while comparing:

```bash
uvicorn app.main:app --reload --port 8001
```

Both apps can point at the same `lungcancer.csv`; the FastAPI app has its own
database file, so the Django one is never touched.
