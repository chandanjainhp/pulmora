"""Shared prediction pipeline used by both the JSON API (/predict) and the
browser form flow (/pages/predict).

Replicates the body of the original Django ``predict`` view: model inference,
risk-factor construction, premium calculation, doctor recommendation and the
digital signature — then persists the result so a PDF can be regenerated.
"""
from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import PredictionInput
from app.services.doctors import get_doctor_recommendation
from app.services.ml_service import MLModel
from app.services.premium import build_risk_factors, calculate_premium


def run_prediction(
    db: Session, user: User, payload: PredictionInput, ml_model: MLModel
) -> Prediction:
    # --- Model inference (same order as the original views.py array) ---
    result = ml_model.predict(payload.feature_array())
    diagnosis = result["diagnosis"]

    # --- Risk factors, premium, doctor (verbatim business rules) ---
    risk_factors = build_risk_factors(
        payload.age,
        payload.air_pollution,
        payload.alcohol_use,
        payload.dust_allergy,
        payload.occupational_hazards,
        payload.genetic_risk,
        payload.chronic_lung_disease,
        payload.smoking,
        payload.passive_smoker,
        payload.chest_pain,
        payload.coughing_of_blood,
    )
    premium_amount, premium_factors = calculate_premium(
        payload.age, payload.gender, diagnosis, risk_factors
    )
    doctor = get_doctor_recommendation(diagnosis)

    # --- Digital signature (same format as views.py) ---
    digital_signature = (
        "Verified by Pulmora on "
        f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    report_date = datetime.datetime.now().strftime("%Y-%m-%d")

    prediction = Prediction(
        user_id=user.id,
        age=payload.age,
        gender=payload.gender,
        air_pollution=payload.air_pollution,
        alcohol_use=payload.alcohol_use,
        dust_allergy=payload.dust_allergy,
        occupational_hazards=payload.occupational_hazards,
        genetic_risk=payload.genetic_risk,
        chronic_lung_disease=payload.chronic_lung_disease,
        balanced_diet=payload.balanced_diet,
        obesity=payload.obesity,
        smoking=payload.smoking,
        passive_smoker=payload.passive_smoker,
        chest_pain=payload.chest_pain,
        coughing_of_blood=payload.coughing_of_blood,
        fatigue=payload.fatigue,
        weight_loss=payload.weight_loss,
        shortness_of_breath=payload.shortness_of_breath,
        wheezing=payload.wheezing,
        swallowing_difficulty=payload.swallowing_difficulty,
        clubbing_of_finger_nails=payload.clubbing_of_finger_nails,
        frequent_cold=payload.frequent_cold,
        dry_cough=payload.dry_cough,
        snoring=payload.snoring,
        diagnosis=diagnosis,
        diagnosis_code=result["diagnosis_code"],
        probability=result["probability"],
        risk_factors=risk_factors,
        premium_amount=premium_amount,
        premium_factors=premium_factors,
        doctor=doctor,
        digital_signature=digital_signature,
        report_date=report_date,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
