"""Server-rendered HTML pages, reusing the original Django templates.

Routes mirror the original URLs but live under /pages/*:

    /pages/home      -> home.html      (was: / and /home)
    /pages/signup    -> signup.html    (was: /signup)
    /pages/signin    -> signin.html    (was: /signin)
    /pages/predict   -> predict.html   (was: /predict)
    /pages/logout    -> redirect       (was: /logout, no URL was wired in Django)

Authentication for the browser flow uses a JWT stored in an HttpOnly,
SameSite=Strict cookie (see MIGRATION_NOTES.md - CSRF section).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.prediction import PredictionInput, PredictionResponse
from app.services.pipeline import run_prediction
from app.services.pdf_report import build_report_context, generate_pdf_bytes, pdf_response

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["static"] = lambda path: f"/static/{path.lstrip('/')}"

router = APIRouter(prefix="/pages", tags=["pages"])

# Original form field names (with spaces) -> PredictionInput field names.
FORM_FIELD_MAP = {
    "Age": "age",
    "Gender": "gender",
    "Air Pollution": "air_pollution",
    "Alcohol use": "alcohol_use",
    "Dust Allergy": "dust_allergy",
    "OccuPational Hazards": "occupational_hazards",
    "Genetic Risk": "genetic_risk",
    "chronic Lung Disease": "chronic_lung_disease",
    "Balanced Diet": "balanced_diet",
    "Obesity": "obesity",
    "Smoking": "smoking",
    "Passive Smoker": "passive_smoker",
    "Chest Pain": "chest_pain",
    "Coughing of Blood": "coughing_of_blood",
    "Fatigue": "fatigue",
    "Weight Loss": "weight_loss",
    "Shortness of Breath": "shortness_of_breath",
    "Wheezing": "wheezing",
    "Swallowing Difficulty": "swallowing_difficulty",
    "Clubbing of Finger Nails": "clubbing_of_finger_nails",
    "Frequent Cold": "frequent_cold",
    "Dry Cough": "dry_cough",
    "Snoring": "snoring",
}


def _current_user_optional(request: Request, db: Session) -> Optional[User]:
    """Return the signed-in user (cookie) or None - for HTML pages."""
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        return None
    username = decode_access_token(token)
    if not username:
        return None
    return db.query(User).filter(User.username == username).first()


def _require_page_user(request: Request, db: Session) -> Optional[User]:
    user = _current_user_optional(request, db)
    if user is None:
        return None
    return user


def _render(request: Request, name: str, context: dict) -> HTMLResponse:
    context.setdefault("messages", request.query_params.getlist("msg"))
    return templates.TemplateResponse(request=request, name=name, context=context)


# --- Home --------------------------------------------------------------------

@router.get("/home", summary="Landing page")
async def home(request: Request):
    return _render(request, "home.html", {})


# --- Signup ------------------------------------------------------------------

@router.get("/signup", summary="Signup form")
async def signup_page(request: Request):
    return _render(request, "signup.html", {})


@router.post("/signup", summary="Create account (browser flow)")
async def signup(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    first_name = form.get("first_name", "")
    last_name = form.get("last_name", "")
    username = form.get("username", "")
    password1 = form.get("password1", "")
    password2 = form.get("password2", "")
    email = form.get("email", "")

    # Same rules / messages as the original signup view.
    if password1 != password2:
        return RedirectResponse(
            "/pages/signup?msg=Password+not+matching..", status_code=303
        )
    if db.query(User).filter(User.username == username).first():
        return RedirectResponse("/pages/signup?msg=Username+Taken", status_code=303)
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse(
            "/pages/signup?msg=Email+already+exists", status_code=303
        )

    db.add(
        User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            hashed_password=hash_password(password1),
        )
    )
    db.commit()
    return RedirectResponse("/pages/signin", status_code=303)


# --- Signin ------------------------------------------------------------------

@router.get("/signin", summary="Sign-in form")
async def signin_page(request: Request):
    return _render(request, "signin.html", {})


@router.post("/signin", summary="Sign in (browser flow, sets JWT cookie)")
async def signin(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = form.get("username", "")
    password = form.get("password", "")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(
        password, user.hashed_password, user.legacy_password_hash
    ):
        return RedirectResponse(
            "/pages/signin?msg=invalid+credentials", status_code=303
        )

    # Transparent hash upgrade for users imported from Django.
    if user.legacy_password_hash is not None:
        user.hashed_password = hash_password(password)
        user.legacy_password_hash = None
        db.commit()

    response = RedirectResponse("/pages/predict", status_code=303)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=create_access_token(subject=user.username),
        httponly=True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response


# --- Logout ------------------------------------------------------------------

@router.get("/logout", summary="Sign out (clears the JWT cookie)")
async def logout():
    response = RedirectResponse("/pages/home", status_code=303)
    response.delete_cookie(settings.AUTH_COOKIE_NAME)
    return response


# --- Predict -----------------------------------------------------------------

@router.get("/predict", summary="Prediction form (requires sign-in)")
async def predict_page(request: Request, db: Session = Depends(get_db)):
    if _require_page_user(request, db) is None:
        return RedirectResponse("/pages/signin?msg=Please+sign+in+first", status_code=303)
    return _render(request, "predict.html", {"show_results": False})


@router.post("/predict", summary="Submit the prediction form (browser flow)")
async def predict_submit(
    request: Request, db: Session = Depends(get_db)
):
    user = _require_page_user(request, db)
    if user is None:
        return RedirectResponse("/pages/signin?msg=Please+sign+in+first", status_code=303)

    form = await request.form()
    generate_pdf = "generate_pdf" in form

    # Map the original form field names onto the validated schema.
    data: dict = {}
    try:
        for form_name, schema_name in FORM_FIELD_MAP.items():
            if form_name not in form:
                raise ValueError(f"Missing field: {form_name}")
            data[schema_name] = int(form[form_name])
        payload = PredictionInput(**data)
    except (ValueError, TypeError) as exc:
        return _render(
            request,
            "predict.html",
            {"show_results": False, "messages": [f"Invalid input: {exc}"]},
        )

    prediction = run_prediction(db, user, payload, request.app.state.ml_model)
    response_model = PredictionResponse.model_validate(prediction, from_attributes=True)

    if generate_pdf:
        context = build_report_context(
            user=user,
            diagnosis=prediction.diagnosis,
            age=prediction.age,
            gender=prediction.gender,
            risk_factors=prediction.risk_factors,
            premium_amount=prediction.premium_amount,
            premium_factors=prediction.premium_factors,
            doctor=prediction.doctor,
            digital_signature=prediction.digital_signature,
            report_date=prediction.report_date,
        )
        return pdf_response(generate_pdf_bytes(context), user.username)

    # Same context keys the original view passed to predict.html.
    return _render(
        request,
        "predict.html",
        {
            "show_results": True,
            "diagnosis": prediction.diagnosis,
            "premium_amount": prediction.premium_amount,
            "doctor": prediction.doctor,
            "age": prediction.age,
            "gender": prediction.gender,
            "air_pollution": prediction.air_pollution,
            "alcohol_use": prediction.alcohol_use,
            "dust_allergy": prediction.dust_allergy,
            "occupational_hazards": prediction.occupational_hazards,
            "genetic_risk": prediction.genetic_risk,
            "chronic_lung_disease": prediction.chronic_lung_disease,
            "balanced_diet": prediction.balanced_diet,
            "obesity": prediction.obesity,
            "smoking": prediction.smoking,
            "passive_smoker": prediction.passive_smoker,
            "chest_pain": prediction.chest_pain,
            "coughing_of_blood": prediction.coughing_of_blood,
            "fatigue": prediction.fatigue,
            "weight_loss": prediction.weight_loss,
            "shortness_of_breath": prediction.shortness_of_breath,
            "wheezing": prediction.wheezing,
            "swallowing_difficulty": prediction.swallowing_difficulty,
            "clubbing_of_finger_nails": prediction.clubbing_of_finger_nails,
            "frequent_cold": prediction.frequent_cold,
            "dry_cough": prediction.dry_cough,
            "snoring": prediction.snoring,
            "probability": response_model.probability,
            "prediction_id": prediction.id,
        },
    )
