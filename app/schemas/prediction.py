"""Pydantic schemas for the 22-feature prediction request/response."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Validation matching the original HTML form ------------------------------
# Age:    <input type="number" min="1" required>  (JS: minimum age is 1)
# Gender: radio buttons, 1 = male, 2 = female
# All symptom scales: <input type="range" min="1" max="8">
#
# NOTE: the training dataset contains a few 9s for some symptoms, but the
# original UI never allowed submitting them, so the API enforces 1..8 to match
# the form (see MIGRATION_NOTES.md).

RangeField = Field(ge=1, le=8, description="Scale value between 1 and 8")


class PredictionInput(BaseModel):
    age: int = Field(ge=1, le=120, description="Patient age in years (min 1)")
    gender: Literal[1, 2] = Field(description="1 = male, 2 = female")
    air_pollution: int = RangeField
    alcohol_use: int = RangeField
    dust_allergy: int = RangeField
    occupational_hazards: int = RangeField
    genetic_risk: int = RangeField
    chronic_lung_disease: int = RangeField
    balanced_diet: int = RangeField
    obesity: int = RangeField
    smoking: int = RangeField
    passive_smoker: int = RangeField
    chest_pain: int = RangeField
    coughing_of_blood: int = RangeField
    fatigue: int = RangeField
    weight_loss: int = RangeField
    shortness_of_breath: int = RangeField
    wheezing: int = RangeField
    swallowing_difficulty: int = RangeField
    clubbing_of_finger_nails: int = RangeField
    frequent_cold: int = RangeField
    dry_cough: int = RangeField
    snoring: int = RangeField

    def feature_array(self) -> list[int]:
        """Feature vector in the exact column order of lungcancer.csv."""
        return [
            self.age,
            self.gender,
            self.air_pollution,
            self.alcohol_use,
            self.dust_allergy,
            self.occupational_hazards,
            self.genetic_risk,
            self.chronic_lung_disease,
            self.balanced_diet,
            self.obesity,
            self.smoking,
            self.passive_smoker,
            self.chest_pain,
            self.coughing_of_blood,
            self.fatigue,
            self.weight_loss,
            self.shortness_of_breath,
            self.wheezing,
            self.swallowing_difficulty,
            self.clubbing_of_finger_nails,
            self.frequent_cold,
            self.dry_cough,
            self.snoring,
        ]


# --- Response models ---------------------------------------------------------


class RiskFactor(BaseModel):
    name: str
    value: int
    risk_level: Literal["Low", "Medium", "High"]


class PremiumFactor(BaseModel):
    name: str
    impact: float


class Doctor(BaseModel):
    name: str
    specialty: str
    hospital: str
    contact: str
    recommendation: str


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    diagnosis: str
    diagnosis_code: int
    probability: float
    risk_factors: list[RiskFactor]
    premium_amount: float
    premium_factors: list[PremiumFactor]
    doctor: Doctor
    digital_signature: str
    report_date: str
