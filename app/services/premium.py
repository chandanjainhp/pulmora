"""Insurance premium calculation and risk-factor construction.

PORTED VERBATIM from the original ``Home/views.py`` (calculate_premium and the
risk_factors list built inside the ``predict`` view).  All thresholds,
formulas and constants are unchanged.

>>> IMPORTANT — bug-compatible behaviour, kept deliberately <<<
The original loop does

    risk_premium += impact if 'impact' in locals() else 0

``impact`` is never reset between iterations, so any factor that matches no
branch re-uses the *previous* factor's impact value.  This is a real bug in
the original code, but it changes the quoted premium, so the FastAPI port
reproduces it exactly to keep prices identical.  See MIGRATION_NOTES.md
("Premium calculation carries a latent bug") before "fixing" it.
"""
from __future__ import annotations

from app.core.config import settings


def build_risk_factors(
    age: int,
    air_pollution: int,
    alcohol_use: int,
    dust_allergy: int,
    occupational_hazards: int,
    genetic_risk: int,
    chronic_lung_disease: int,
    smoking: int,
    passive_smoker: int,
    chest_pain: int,
    coughing_of_blood: int,
) -> list[dict]:
    """The 11 risk factors shown in the report (exact thresholds from views.py)."""
    return [
        {"name": "Age", "value": age,
         "risk_level": "High" if age > 60 else "Medium" if age > 40 else "Low"},
        {"name": "Air Pollution", "value": air_pollution,
         "risk_level": "High" if air_pollution > 6 else "Medium" if air_pollution > 3 else "Low"},
        {"name": "Alcohol use", "value": alcohol_use,
         "risk_level": "High" if alcohol_use > 6 else "Medium" if alcohol_use > 3 else "Low"},
        {"name": "Dust Allergy", "value": dust_allergy,
         "risk_level": "High" if dust_allergy > 6 else "Medium" if dust_allergy > 3 else "Low"},
        {"name": "OccuPational Hazards", "value": occupational_hazards,
         "risk_level": "High" if occupational_hazards > 6 else "Medium" if occupational_hazards > 3 else "Low"},
        {"name": "Genetic Risk", "value": genetic_risk,
         "risk_level": "High" if genetic_risk > 6 else "Medium" if genetic_risk > 3 else "Low"},
        {"name": "chronic Lung Disease", "value": chronic_lung_disease,
         "risk_level": "High" if chronic_lung_disease > 6 else "Medium" if chronic_lung_disease > 3 else "Low"},
        {"name": "Smoking", "value": smoking,
         "risk_level": "High" if smoking > 6 else "Medium" if smoking > 3 else "Low"},
        {"name": "Passive Smoker", "value": passive_smoker,
         "risk_level": "High" if passive_smoker > 6 else "Medium" if passive_smoker > 3 else "Low"},
        {"name": "Chest Pain", "value": chest_pain,
         "risk_level": "High" if chest_pain > 6 else "Medium" if chest_pain > 3 else "Low"},
        {"name": "Coughing of Blood", "value": coughing_of_blood,
         "risk_level": "High" if coughing_of_blood > 6 else "Medium" if coughing_of_blood > 3 else "Low"},
    ]


def calculate_premium(
    age: int, gender: int, diagnosis: str, risk_factors: list[dict]
) -> tuple[float, list[dict]]:
    """Insurance premium in INR plus a breakdown of factors.

    Exact port of ``calculate_premium`` from Home/views.py (including the
    loop-carried ``impact`` variable — see module docstring).
    """
    # Base premium amount
    base_premium = 50.0

    # Age factor (higher age = higher premium)
    age_factor = age / 10

    # Gender factor (slightly higher for males based on statistical risk)
    gender_factor = 1.1 if gender == 1 else 1.0

    # Diagnosis factor
    if diagnosis == "Positive":
        diagnosis_factor = 3.0
    elif diagnosis == "Medium":
        diagnosis_factor = 1.5
    else:
        diagnosis_factor = 1.0

    # Risk factors calculation
    risk_premium = 0
    premium_factors: list[dict] = []

    # Calculate premium impact for each risk factor
    for factor in risk_factors:
        if factor["name"] == "Age":
            impact = age_factor * 5
            premium_factors.append({"name": "Age Factor", "impact": round(impact, 2)})
        elif factor["name"] == "Smoking" and factor["value"] > 4:
            impact = factor["value"] * 3
            premium_factors.append({"name": "Smoking", "impact": round(impact, 2)})
        elif factor["name"] == "Genetic Risk" and factor["value"] > 4:
            impact = factor["value"] * 2.5
            premium_factors.append({"name": "Genetic Risk", "impact": round(impact, 2)})
        elif factor["name"] == "chronic Lung Disease" and factor["value"] > 4:
            impact = factor["value"] * 2.8
            premium_factors.append(
                {"name": "Chronic Lung Disease", "impact": round(impact, 2)}
            )
        elif factor["value"] > 5:
            impact = factor["value"] * 1.2
            premium_factors.append(
                {"name": factor["name"], "impact": round(impact, 2)}
            )

        # Bug-compatible with the original Django code: `impact` is NOT reset
        # between iterations, so unmatched factors reuse the previous impact.
        risk_premium += impact if "impact" in locals() else 0  # noqa: F821

    # Base premium factor
    premium_factors.append({"name": "Base Premium", "impact": base_premium})

    # Diagnosis impact
    diagnosis_impact = base_premium * (diagnosis_factor - 1)
    if diagnosis_impact > 0:
        premium_factors.append(
            {"name": "Diagnosis Risk", "impact": round(diagnosis_impact, 2)}
        )

    # Calculate total premium (in USD)
    total_premium_usd = (base_premium + risk_premium) * diagnosis_factor * gender_factor

    # Convert to Indian Rupees (1 USD = approximately 75 INR, as in views.py)
    inr_conversion_rate = settings.INR_CONVERSION_RATE
    total_premium_inr = total_premium_usd * inr_conversion_rate

    # Convert premium factors to INR
    for factor in premium_factors:
        factor["impact"] = round(factor["impact"] * inr_conversion_rate, 2)

    return round(total_premium_inr, 2), premium_factors
